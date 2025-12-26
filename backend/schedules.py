from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import SCHEDULED_FILE_PATH
from notifications import send_email
from plugs import Plug, plug_manager


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
    logging.info(f"Cleared automatic schedules for {plug_address}")


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
    logging.info(f"Created {event_type} scheduled event: {event}")
    return event


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
            logging.info(f"Cancelled scheduled event: {event}")
            _save_scheduled_events(events)
            return True
    return False


def process_scheduled_events(manager_from_email: str, manager_to_email: str):
    """Process pending scheduled events and execute if time has arrived."""
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)
    modified = False

    for event in events:
        if event['status'] != 'pending':
            continue

        target_dt = datetime.fromisoformat(event['target_datetime'])

        if target_dt <= now:
            # Time to execute
            plug_address = event['plug_address']
            plug_name = event.get('plug_name', 'Unknown')
            desired_state = event.get('desired_state', True)  # Default to ON for backward compatibility

            # Find the plug from shared plug manager
            plug = plug_manager.get_plug_by_address(plug_address)
            if plug:
                try:
                    # Cancel all countdown timers first to avoid Tapo API errors
                    plug.cancel_countdown_rules()

                    # Turn plug to desired state
                    if desired_state:
                        plug.tapo.turnOn()
                        state_str = "ON"
                    else:
                        plug.tapo.turnOff()
                        state_str = "OFF"

                    logging.info(f"Executed scheduled event for {plug_name} at {now}: turned {state_str}")

                    # If duration specified, set opposite state timer
                    duration_seconds = event.get('duration_seconds')
                    if duration_seconds and duration_seconds > 0:
                        if desired_state:
                            plug.tapo.turnOffWithDelay(duration_seconds)
                            logging.info(f"Plug {plug_name} will turn OFF in {timedelta(seconds=duration_seconds)}")
                        else:
                            plug.tapo.turnOnWithDelay(duration_seconds)
                            logging.info(f"Plug {plug_name} will turn ON in {timedelta(seconds=duration_seconds)}")

                    # Send email notification
                    email_message = f"🔌 Plug {plug_name} has been turned {state_str} per scheduled event at {now}."
                    if duration_seconds and duration_seconds > 0:
                        opposite_state = "OFF" if desired_state else "ON"
                        email_message += f"<br>It will turn {opposite_state} in {timedelta(seconds=duration_seconds)}."
                    send_email(
                        f"🔌 Plug {plug_name} scheduled {state_str} executed",
                        email_message,
                        manager_from_email,
                        manager_to_email
                    )

                    event['status'] = 'completed'
                    event['executed_at'] = now.isoformat()
                    modified = True

                except Exception as err:
                    logging.error(f"Error executing scheduled event for {plug_name}: {err}")
                    event['status'] = 'failed'
                    event['error'] = str(err)
                    event['failed_at'] = now.isoformat()
                    modified = True
            else:
                logging.error(f"Plug {plug_address} not found for scheduled event")
                event['status'] = 'failed'
                event['error'] = 'Plug not found'
                event['failed_at'] = now.isoformat()
                modified = True

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
        logging.info(f"Cleaned up {len(events) - len(active_events)} old scheduled events")


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
        if not plug.enabled:
            logging.info(f"Skipping automatic schedule generation for {plug.name} (manual mode)")
            continue

        plug.calculate_target_hours(prices)

        for period_idx, period in enumerate(plug.periods):
            target = period.get('target')
            if not target:
                continue

            target_hour, target_price = target
            runtime_seconds = period['runtime_seconds']

            if runtime_seconds <= 0:
                continue

            # Create datetime for the target hour on target_date
            # Prices are in local time, so create datetime in local timezone first
            # Read system timezone from /etc/timezone (set during Docker build)
            try:
                with open('/etc/timezone', 'r') as f:
                    system_tz = f.read().strip()
                local_tz = ZoneInfo(system_tz)
            except (FileNotFoundError, Exception):
                # Fallback to UTC if /etc/timezone doesn't exist
                local_tz = timezone.utc

            target_dt_local = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                target_hour,
                0,  # minute
                0,  # second
                tzinfo=local_tz
            )
            # Convert to UTC for storage
            target_dt = target_dt_local.astimezone(timezone.utc)

            # Skip if target time is in the past
            if target_dt < now:
                logging.info(f"Skipping past schedule for {plug.name} period {period_idx+1} at {target_dt}")
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
            logging.info(
                f"Created automatic schedule for {plug.name} period {period_idx+1}: "
                f"{target_hour}h ({target_price} €/kWh) for {timedelta(seconds=runtime_seconds)}"
            )

    _save_scheduled_events(events)
    logging.info(f"Generated automatic schedules for {target_date.date()}")
