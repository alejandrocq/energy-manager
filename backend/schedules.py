from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from config import (
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_DELAY_SECONDS,
    RETRY_WINDOW_HOURS,
    SCHEDULED_FILE_PATH,
    TIMEZONE,
)

logger = logging.getLogger("uvicorn.error")
from email_templates import render_schedule_execution_email
from notifications import send_email
from plugs import Plug, plug_manager
from recurrence import calculate_next_occurrence, format_recurrence_pattern, validate_recurrence
from scheduling import PeriodStrategyData, ValleyDetectionStrategyData


def _load_scheduled_events():
    """Load all scheduled events from JSON file."""
    try:
        with open(SCHEDULED_FILE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_scheduled_events(events):
    """Save scheduled events to JSON file."""
    with open(SCHEDULED_FILE_PATH, 'w') as f:
        json.dump(events, f, indent=2)


def _calculate_next_retry_time(retry_count: int, now: datetime) -> datetime:
    """Calculate next retry time using exponential backoff."""
    delay = min(
        RETRY_BASE_DELAY_SECONDS * (2 ** retry_count),
        RETRY_MAX_DELAY_SECONDS
    )
    return now + timedelta(seconds=delay)


def clear_automatic_schedules(plug_address: str):
    """Clear all pending automatic schedules for a specific plug.

    Args:
        plug_address: IP address of the plug
    """
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)

    # Filter out pending automatic schedules for this plug
    events = [
        e for e in events
        if not (e.get('plug_address') == plug_address and
                e.get('type') == 'automatic' and
                e['status'] == 'pending' and
                datetime.fromisoformat(e['target_datetime']) >= now)
    ]

    _save_scheduled_events(events)
    logger.info(f"Cleared automatic schedules [plug_address={plug_address}]")


def create_scheduled_event(plug_address: str, plug_name: str, target_datetime: str, desired_state: bool, duration_seconds: int | None = None, event_type: str = "manual", source_period: int | None = None):
    """Create a new scheduled event for a plug.

    Args:
        plug_address: IP address of the plug
        plug_name: Name of the plug
        target_datetime: When to execute (ISO format string)
        desired_state: True = turn ON, False = turn OFF
        duration_seconds: How long to stay in desired state before reverting
        event_type: "manual" (user-created) or "automatic" (price-based)
        source_period: For automatic events, which period index generated it
    """
    events = _load_scheduled_events()

    # Normalize target_datetime to UTC
    target_dt = datetime.fromisoformat(target_datetime)
    if target_dt.tzinfo is None:
        # Assume UTC if no timezone info
        target_dt = target_dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        target_dt = target_dt.astimezone(timezone.utc)

    event = {
        'id': str(uuid.uuid4()),
        'plug_address': plug_address,
        'plug_name': plug_name,
        'target_datetime': target_dt.isoformat(),  # Always stored as UTC
        'desired_state': desired_state,  # True = ON, False = OFF
        'duration_seconds': duration_seconds,
        'type': event_type,  # "manual" or "automatic"
        'source_period': source_period,  # For automatic events
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    events.append(event)
    _save_scheduled_events(events)
    logger.info(f"Created scheduled event [event_type={event_type}, event={event}]")
    return event


def create_repeating_schedule(plug_address: str, plug_name: str, recurrence: dict, desired_state: bool, duration_seconds: int | None = None) -> dict | None:
    """Create a new repeating schedule for a plug.

    Args:
        plug_address: IP address of the plug
        plug_name: Name of the plug
        recurrence: Recurrence configuration dict
        desired_state: True = turn ON, False = turn OFF
        duration_seconds: How long to stay in desired state before reverting

    Returns:
        Created event dict or None if validation fails
    """
    # Validate recurrence
    is_valid, error = validate_recurrence(recurrence)
    if not is_valid:
        logger.error(f"Invalid recurrence configuration [error={error}]")
        return None

    # Generate parent_id for this repeating schedule series
    parent_id = str(uuid.uuid4())

    # Calculate first occurrence
    now = datetime.now(timezone.utc)
    first_occurrence = calculate_next_occurrence(recurrence, now)

    if first_occurrence is None:
        logger.error("Could not calculate first occurrence for repeating schedule")
        return None

    events = _load_scheduled_events()

    # Add parent_id to recurrence config
    recurrence_with_parent = {**recurrence, 'parent_id': parent_id}

    event = {
        'id': str(uuid.uuid4()),
        'plug_address': plug_address,
        'plug_name': plug_name,
        'target_datetime': first_occurrence.isoformat(),
        'desired_state': desired_state,
        'duration_seconds': duration_seconds,
        'type': 'repeating',
        'recurrence': recurrence_with_parent,
        'status': 'pending',
        'created_at': now.isoformat()
    }

    events.append(event)
    _save_scheduled_events(events)

    pattern = format_recurrence_pattern(recurrence)
    logger.info(f"Created repeating schedule [plug_name={plug_name}, pattern={pattern}, first_occurrence={first_occurrence}]")
    return event


def _generate_next_occurrence(completed_event: dict) -> dict | None:
    """Generate the next occurrence of a repeating schedule after completion.

    Args:
        completed_event: The event that was just completed

    Returns:
        New pending event or None if no more occurrences
    """
    recurrence = completed_event.get('recurrence')
    if not recurrence:
        return None

    # Calculate next occurrence after the completed event's target time
    completed_time = datetime.fromisoformat(completed_event['target_datetime'])
    next_occurrence = calculate_next_occurrence(recurrence, completed_time)

    if next_occurrence is None:
        logger.info(f"No more occurrences for repeating schedule [plug_name={completed_event['plug_name']}, parent_id={recurrence.get('parent_id')}]")
        return None

    now = datetime.now(timezone.utc)

    new_event = {
        'id': str(uuid.uuid4()),
        'plug_address': completed_event['plug_address'],
        'plug_name': completed_event['plug_name'],
        'target_datetime': next_occurrence.isoformat(),
        'desired_state': completed_event['desired_state'],
        'duration_seconds': completed_event.get('duration_seconds'),
        'type': 'repeating',
        'recurrence': recurrence,
        'status': 'pending',
        'created_at': now.isoformat()
    }

    logger.info(f"Generated next occurrence [plug_name={completed_event['plug_name']}, next_time={next_occurrence}]")
    return new_event


def get_scheduled_events(plug_address: str | None = None):
    """Get all scheduled events, optionally filtered by plug address."""
    events = _load_scheduled_events()
    if plug_address:
        events = [e for e in events if e['plug_address'] == plug_address]
    return [e for e in events if e['status'] == 'pending']


def delete_scheduled_event(event_id: str):
    """Delete a scheduled event by ID."""
    events = _load_scheduled_events()
    for event in events:
        if event['id'] == event_id:
            event['status'] = 'cancelled'
            event['cancelled_at'] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Cancelled scheduled event [event={event}]")
            _save_scheduled_events(events)
            return True
    return False


def delete_repeating_schedule(parent_id: str) -> bool:
    """Cancel all pending events for a repeating schedule series.

    Args:
        parent_id: The parent_id that links all occurrences of the repeating schedule

    Returns:
        True if any events were cancelled, False otherwise
    """
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)
    cancelled_count = 0

    for event in events:
        if event.get('type') == 'repeating' and event['status'] == 'pending':
            recurrence = event.get('recurrence', {})
            if recurrence.get('parent_id') == parent_id:
                event['status'] = 'cancelled'
                event['cancelled_at'] = now.isoformat()
                cancelled_count += 1

    if cancelled_count > 0:
        _save_scheduled_events(events)
        logger.info(f"Cancelled repeating schedule series [parent_id={parent_id}, cancelled_count={cancelled_count}]")
        return True

    return False


def get_repeating_schedules(plug_address: str | None = None) -> list[dict]:
    """Get unique repeating schedule definitions.

    Returns one entry per repeating schedule series (grouped by parent_id),
    representing the next pending occurrence.

    Args:
        plug_address: Optional filter by plug address

    Returns:
        List of repeating schedule events (one per series)
    """
    events = _load_scheduled_events()

    # Filter to repeating pending events
    repeating = [
        e for e in events
        if e.get('type') == 'repeating' and e['status'] == 'pending'
    ]

    if plug_address:
        repeating = [e for e in repeating if e['plug_address'] == plug_address]

    # Group by parent_id and return the earliest pending for each
    by_parent: dict[str, dict] = {}
    for event in repeating:
        parent_id = event.get('recurrence', {}).get('parent_id')
        if parent_id:
            if parent_id not in by_parent:
                by_parent[parent_id] = event
            else:
                # Keep the one with earlier target_datetime
                existing_dt = datetime.fromisoformat(by_parent[parent_id]['target_datetime'])
                event_dt = datetime.fromisoformat(event['target_datetime'])
                if event_dt < existing_dt:
                    by_parent[parent_id] = event

    return list(by_parent.values())


def process_scheduled_events(manager_from_email: str | None = None, manager_to_email: str | None = None):
    """Process pending scheduled events and execute if time has arrived.

    Args:
        manager_from_email: Optional sender email for notifications
        manager_to_email: Optional recipient email for notifications
    """
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)
    modified = False

    for event in events:
        if event['status'] != 'pending':
            continue

        target_dt = datetime.fromisoformat(event['target_datetime'])
        next_retry_at = event.get('next_retry_at')

        # Check if we're past the retry window
        retry_window_end = target_dt + timedelta(hours=RETRY_WINDOW_HOURS)
        if now > retry_window_end:
            plug_name = event.get('plug_name', 'Unknown')
            event['status'] = 'failed'
            event['error'] = f"Retry window expired ({RETRY_WINDOW_HOURS}h)"
            event['failed_at'] = now.isoformat()
            modified = True
            logger.error(f"Schedule permanently failed [plug_name={plug_name}, reason=retry_window_expired, retry_count={event.get('retry_count', 0)}]")
            continue

        # Determine when to execute (original target or next retry time)
        execute_time = datetime.fromisoformat(next_retry_at) if next_retry_at else target_dt

        if execute_time <= now:
            # Time to execute
            plug_address = event['plug_address']
            plug_name = event.get('plug_name', 'Unknown')
            desired_state = event.get('desired_state', True)  # Default to ON for backward compatibility

            # Find the plug from shared plug manager
            plug = plug_manager.get_plug_by_address(plug_address)
            if plug:
                try:
                    # Execute all Tapo operations under lock to prevent concurrent access
                    with plug.acquire_lock():
                        # Cancel all countdown timers first to avoid Tapo API errors
                        plug.cancel_countdown_rules()

                        # Turn plug to desired state
                        if desired_state:
                            plug.turn_on()
                            state_str = "ON"
                        else:
                            plug.turn_off()
                            state_str = "OFF"

                        logger.info(f"Executed scheduled event [plug_name={plug_name}, timestamp={now}, state={state_str}]")

                        # If duration specified, set opposite state timer
                        duration_seconds = event.get('duration_seconds')
                        if duration_seconds and duration_seconds > 0:
                            if desired_state:
                                plug.turn_off_with_delay(duration_seconds)
                                logger.info(f"Plug will turn OFF [plug_name={plug_name}, duration={timedelta(seconds=duration_seconds)}]")
                            else:
                                plug.turn_on_with_delay(duration_seconds)
                                logger.info(f"Plug will turn ON [plug_name={plug_name}, duration={timedelta(seconds=duration_seconds)}]")

                    # Send email notification
                    from_state = not desired_state  # Previous state is opposite of desired
                    event_type = event.get('type', 'manual')

                    # Format timestamp
                    timestamp_local = now.astimezone(TIMEZONE)
                    timestamp_str = timestamp_local.strftime("%b %d, %H:%M")

                    # Build duration info if applicable
                    duration_info = ""
                    if duration_seconds and duration_seconds > 0:
                        opposite_state = "OFF" if desired_state else "ON"
                        duration_td = timedelta(seconds=duration_seconds)
                        # Format duration nicely
                        hours = duration_td.seconds // 3600
                        minutes = (duration_td.seconds % 3600) // 60
                        if hours > 0 and minutes > 0:
                            duration_str = f"{hours}h {minutes}m"
                        elif hours > 0:
                            duration_str = f"{hours}h"
                        else:
                            duration_str = f"{minutes}m"
                        duration_info = f"Will turn {opposite_state} in {duration_str}"

                    # Send email notification if configured
                    if manager_from_email and manager_to_email:
                        email_html = render_schedule_execution_email(
                            plug_name=plug_name,
                            event_type=event_type,
                            from_state=from_state,
                            to_state=desired_state,
                            timestamp=timestamp_str,
                            duration_info=duration_info
                        )

                        send_email(
                            f"🔌 Plug {plug_name} scheduled {state_str} executed",
                            email_html,
                            manager_from_email,
                            manager_to_email,
                            attach_chart=False
                        )

                    event['status'] = 'completed'
                    event['executed_at'] = now.isoformat()
                    modified = True

                    # Generate next occurrence for repeating schedules
                    if event.get('type') == 'repeating':
                        next_event = _generate_next_occurrence(event)
                        if next_event:
                            events.append(next_event)

                except Exception as err:
                    # Schedule retry with exponential backoff
                    retry_count = event.get('retry_count', 0) + 1
                    event['retry_count'] = retry_count
                    event['last_error'] = str(err)
                    next_retry = _calculate_next_retry_time(retry_count, now)
                    event['next_retry_at'] = next_retry.isoformat()
                    modified = True
                    logger.warning(f"Schedule execution failed, will retry [plug_name={plug_name}, error={err}, retry_count={retry_count}, next_retry={next_retry}]")
            else:
                # Plug not found - schedule retry (config might change)
                retry_count = event.get('retry_count', 0) + 1
                event['retry_count'] = retry_count
                event['last_error'] = 'Plug not found'
                next_retry = _calculate_next_retry_time(retry_count, now)
                event['next_retry_at'] = next_retry.isoformat()
                modified = True
                logger.warning(f"Plug not found, will retry [plug_address={plug_address}, retry_count={retry_count}, next_retry={next_retry}]")

    if modified:
        _save_scheduled_events(events)

    # Clean up old completed/cancelled events (older than 7 days)
    _cleanup_old_events()


def _cleanup_old_events():
    """Remove old completed/cancelled events from storage."""
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    active_events = []
    for e in events:
        if e['status'] == 'pending':
            active_events.append(e)
            continue

        event_dt = datetime.fromisoformat(e.get('created_at') or e.get('cancelled_at') or e.get('executed_at') or now.isoformat())

        if event_dt > cutoff:
            active_events.append(e)

    if len(active_events) != len(events):
        _save_scheduled_events(active_events)
        logger.info(f"Cleaned up old scheduled events [count={len(events) - len(active_events)}]")


def generate_automatic_schedules(plugs: list[Plug], prices: list[tuple[int, float]], target_date: datetime):
    """Generate automatic schedules for all enabled plugs based on electricity prices.

    This function:
    1. Clears existing pending automatic schedules
    2. For each enabled plug (automatic mode):
       - Calculates cheapest hour in each configured period
       - Creates schedule to turn plug ON at that hour
       - Duration is set to the period's runtime

    Args:
        plugs: List of Plug objects
        prices: List of (hour, price) tuples for the target date
        target_date: The date these schedules are for
    """
    events = _load_scheduled_events()

    # Remove existing pending automatic schedules for today/future
    now = datetime.now(timezone.utc)
    events = [
        e for e in events
        if not (e.get('type') == 'automatic' and e['status'] == 'pending' and datetime.fromisoformat(e['target_datetime']) >= now)
    ]

    # Generate new automatic schedules
    for plug in plugs:
        if not plug.automatic_schedules:
            logger.info(f"Skipping automatic schedule generation [plug_name={plug.name}, reason=manual_mode]")
            continue

        plug.calculate_target_hours(prices)

        if isinstance(plug.strategy_data, ValleyDetectionStrategyData):
            # For valley detection, group contiguous hours into valleys and create one event per valley
            target_hours = plug.strategy_data.target_hours
            total_runtime = plug.strategy_data.runtime_seconds

            if not target_hours or total_runtime <= 0:
                continue

            # Group contiguous hours into valleys
            valleys = []
            current_valley = [target_hours[0]]

            for i in range(1, len(target_hours)):
                if target_hours[i] == target_hours[i-1] + 1:
                    # Contiguous hour, add to current valley
                    current_valley.append(target_hours[i])
                else:
                    # Gap found, start new valley
                    valleys.append(current_valley)
                    current_valley = [target_hours[i]]

            # Don't forget the last valley
            valleys.append(current_valley)

            # Calculate runtime per valley
            runtime_per_valley = total_runtime // len(valleys)
            price_map = {h: p for h, p in prices}

            for valley in valleys:
                valley_start_hour = valley[0]
                valley_hours_str = f"[{', '.join(map(str, valley))}]"
                avg_price = sum(price_map.get(h, 0) for h in valley) / len(valley)

                # Create datetime for the valley start
                target_dt_local = datetime(
                    target_date.year,
                    target_date.month,
                    target_date.day,
                    valley_start_hour,
                    0,  # minute
                    0,  # second
                    tzinfo=TIMEZONE
                )
                target_dt = target_dt_local.astimezone(timezone.utc)

                # Skip if target time is in the past
                if target_dt < now:
                    logger.info(f"Skipping past schedule [plug_name={plug.name}, valley={valley_hours_str}, target_time={target_dt}]")
                    continue

                # Create automatic schedule event for this valley
                event = {
                    'id': str(uuid.uuid4()),
                    'plug_address': plug.address,
                    'plug_name': plug.name,
                    'target_datetime': target_dt.isoformat(),
                    'desired_state': True,
                    'duration_seconds': runtime_per_valley,
                    'type': 'automatic',
                    'source_period': 0,
                    'status': 'pending',
                    'created_at': now.isoformat()
                }
                events.append(event)
                logger.info(f"Created automatic schedule [plug_name={plug.name}, strategy=valley_detection, valley={valley_hours_str}, avg_price={avg_price:.4f}, duration={timedelta(seconds=runtime_per_valley)}]")

        elif isinstance(plug.strategy_data, PeriodStrategyData):
            # For period strategy (existing behavior)
            for period_idx, period in enumerate(plug.strategy_data.periods):
                if period.target_hour is None:
                    continue

                target_hour = period.target_hour
                target_price = period.target_price
                runtime_seconds = period.runtime_seconds

                if runtime_seconds <= 0:
                    continue

                # Create datetime for the target hour on target_date
                target_dt_local = datetime(
                    target_date.year,
                    target_date.month,
                    target_date.day,
                    target_hour,
                    0,  # minute
                    0,  # second
                    tzinfo=TIMEZONE
                )
                # Convert to UTC for storage
                target_dt = target_dt_local.astimezone(timezone.utc)

                # Skip if target time is in the past
                if target_dt < now:
                    logger.info(f"Skipping past schedule [plug_name={plug.name}, period={period_idx+1}, target_time={target_dt}]")
                    continue

                # Create automatic schedule event
                event = {
                    'id': str(uuid.uuid4()),
                    'plug_address': plug.address,
                    'plug_name': plug.name,
                    'target_datetime': target_dt.isoformat(),
                    'desired_state': True,  # Turn ON at cheapest hour
                    'duration_seconds': runtime_seconds,
                    'type': 'automatic',
                    'source_period': period_idx,
                    'status': 'pending',
                    'created_at': now.isoformat()
                }
                events.append(event)
                logger.info(f"Created automatic schedule [plug_name={plug.name}, strategy=period, period={period_idx+1}, hour={target_hour}, price={target_price:.4f}, duration={timedelta(seconds=runtime_seconds)}]")

    _save_scheduled_events(events)
    logger.info(f"Generated automatic schedules [date={target_date.date()}]")
