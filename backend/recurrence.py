from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from typing import Literal

from config import TIMEZONE

FrequencyType = Literal['daily', 'weekly', 'monthly', 'custom']

DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def validate_recurrence(recurrence: dict) -> tuple[bool, str | None]:
    """Validate recurrence configuration.

    Returns:
        Tuple of (is_valid, error_message)
    """
    frequency = recurrence.get('frequency')
    if frequency not in ('daily', 'weekly', 'monthly', 'custom'):
        return False, f"Invalid frequency: {frequency}"

    interval = recurrence.get('interval', 1)
    if not isinstance(interval, int) or interval < 1:
        return False, "Interval must be a positive integer"

    time_str = recurrence.get('time')
    if not time_str:
        return False, "Time is required"
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError()
    except (ValueError, AttributeError):
        return False, f"Invalid time format: {time_str} (expected HH:MM)"

    days_of_week = recurrence.get('days_of_week')
    if days_of_week is not None:
        if not isinstance(days_of_week, list):
            return False, "days_of_week must be a list"
        for d in days_of_week:
            if not isinstance(d, int) or not (0 <= d <= 6):
                return False, f"Invalid day of week: {d} (must be 0-6)"

    days_of_month = recurrence.get('days_of_month')
    if days_of_month is not None:
        if not isinstance(days_of_month, list):
            return False, "days_of_month must be a list"
        for d in days_of_month:
            if not isinstance(d, int) or not (1 <= d <= 31):
                return False, f"Invalid day of month: {d} (must be 1-31)"

    # Validate based on frequency
    if frequency == 'weekly' and not days_of_week:
        return False, "Weekly frequency requires days_of_week"
    if frequency == 'monthly' and not days_of_month:
        return False, "Monthly frequency requires days_of_month"
    if frequency == 'custom' and not days_of_week and not days_of_month:
        return False, "Custom frequency requires days_of_week or days_of_month"

    # Validate end_date if provided
    end_date = recurrence.get('end_date')
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=TIMEZONE)
            if end_dt < datetime.now(TIMEZONE):
                return False, "End date cannot be in the past"
        except ValueError:
            return False, f"Invalid end_date format: {end_date}"

    return True, None


def calculate_next_occurrence(recurrence: dict, after: datetime) -> datetime | None:
    """Calculate the next occurrence of a repeating schedule.

    Args:
        recurrence: Recurrence configuration dict
        after: Find next occurrence after this datetime

    Returns:
        Next occurrence datetime (UTC) or None if no more occurrences
    """
    frequency = recurrence['frequency']
    interval = recurrence.get('interval', 1)
    time_str = recurrence['time']
    days_of_week = recurrence.get('days_of_week')
    days_of_month = recurrence.get('days_of_month')
    end_date = recurrence.get('end_date')

    # Parse time
    hour, minute = map(int, time_str.split(':'))

    # Convert 'after' to local timezone for calculations
    if after.tzinfo is None:
        after = after.replace(tzinfo=timezone.utc)
    after_local = after.astimezone(TIMEZONE)

    # Parse end_date if provided
    end_dt = None
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=TIMEZONE)

    if frequency == 'daily':
        next_dt = _next_daily(after_local, hour, minute, interval)
    elif frequency == 'weekly':
        next_dt = _next_weekly(after_local, hour, minute, days_of_week, interval)
    elif frequency == 'monthly':
        next_dt = _next_monthly(after_local, hour, minute, days_of_month, interval)
    elif frequency == 'custom':
        next_dt = _next_custom(after_local, hour, minute, days_of_week, days_of_month, interval)
    else:
        return None

    if next_dt is None:
        return None

    # Check end date
    if end_dt and next_dt > end_dt:
        return None

    # Convert back to UTC for storage
    return next_dt.astimezone(timezone.utc)


def _next_daily(after: datetime, hour: int, minute: int, interval: int) -> datetime:
    """Calculate next daily occurrence."""
    # Start from the day of 'after'
    candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If candidate is not after 'after', move to next day
    if candidate <= after:
        candidate += timedelta(days=1)

    # Apply interval - find the next valid interval day
    if interval > 1:
        # Calculate days since some reference point
        reference = datetime(2000, 1, 1, tzinfo=TIMEZONE)
        days_since_ref = (candidate.date() - reference.date()).days
        remainder = days_since_ref % interval
        if remainder != 0:
            candidate += timedelta(days=(interval - remainder))

    return candidate


def _next_weekly(after: datetime, hour: int, minute: int, days_of_week: list[int], interval: int) -> datetime | None:
    """Calculate next weekly occurrence."""
    if not days_of_week:
        return None

    days_of_week = sorted(set(days_of_week))

    # Start from after
    candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If time has passed today, start from tomorrow
    if candidate <= after:
        candidate += timedelta(days=1)

    # Reference for interval calculation (start of week)
    reference_week = datetime(2000, 1, 3, tzinfo=TIMEZONE)  # Monday, Jan 3, 2000

    # Search for next valid day (limit to prevent infinite loop)
    for _ in range(interval * 7 * 52):  # Max ~1 year search
        current_weekday = candidate.weekday()

        if current_weekday in days_of_week:
            # Check if this week is valid for interval
            if interval > 1:
                weeks_since_ref = (candidate.date() - reference_week.date()).days // 7
                if weeks_since_ref % interval == 0:
                    return candidate
                # Skip to next interval week
                weeks_to_skip = interval - (weeks_since_ref % interval)
                candidate += timedelta(weeks=weeks_to_skip)
                candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # Reset to first valid day of that week
                while candidate.weekday() not in days_of_week:
                    candidate += timedelta(days=1)
                return candidate
            else:
                return candidate

        candidate += timedelta(days=1)

    return None


def _next_monthly(after: datetime, hour: int, minute: int, days_of_month: list[int], interval: int) -> datetime | None:
    """Calculate next monthly occurrence."""
    if not days_of_month:
        return None

    days_of_month = sorted(set(days_of_month))

    # Start from after
    candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If time has passed today, start from tomorrow
    if candidate <= after:
        candidate += timedelta(days=1)

    # Reference for interval calculation
    reference_month = datetime(2000, 1, 1, tzinfo=TIMEZONE)

    # Search for next valid day (limit to prevent infinite loop)
    for _ in range(interval * 31 * 12):  # Max ~1 year search
        year = candidate.year
        month = candidate.month
        day = candidate.day

        # Get last day of current month
        _, last_day = calendar.monthrange(year, month)

        # Check if current day matches any day_of_month
        for dom in days_of_month:
            # Handle days that don't exist in this month (e.g., 31st in Feb)
            actual_day = min(dom, last_day)

            if day <= actual_day:
                test_date = candidate.replace(day=actual_day)

                # Ensure it's after our start point
                if test_date > after:
                    # Check interval
                    if interval > 1:
                        months_since_ref = (year - reference_month.year) * 12 + (month - reference_month.month)
                        if months_since_ref % interval == 0:
                            return test_date
                    else:
                        return test_date

        # Move to first day of next month
        if month == 12:
            candidate = candidate.replace(year=year + 1, month=1, day=1)
        else:
            candidate = candidate.replace(month=month + 1, day=1)

    return None


def _next_custom(after: datetime, hour: int, minute: int, days_of_week: list[int] | None, days_of_month: list[int] | None, interval: int) -> datetime | None:
    """Calculate next custom occurrence (any combination of days)."""
    # Custom allows either or both days_of_week and days_of_month
    candidates = []

    if days_of_week:
        weekly_next = _next_weekly(after, hour, minute, days_of_week, interval)
        if weekly_next:
            candidates.append(weekly_next)

    if days_of_month:
        monthly_next = _next_monthly(after, hour, minute, days_of_month, interval)
        if monthly_next:
            candidates.append(monthly_next)

    if not candidates:
        return None

    return min(candidates)


def format_recurrence_pattern(recurrence: dict) -> str:
    """Format recurrence configuration as human-readable string."""
    frequency = recurrence['frequency']
    interval = recurrence.get('interval', 1)
    time_str = recurrence['time']
    days_of_week = recurrence.get('days_of_week', [])
    days_of_month = recurrence.get('days_of_month', [])

    parts = []

    if frequency == 'daily':
        if interval == 1:
            parts.append("Daily")
        else:
            parts.append(f"Every {interval} days")
    elif frequency == 'weekly':
        if interval == 1:
            parts.append("Weekly")
        else:
            parts.append(f"Every {interval} weeks")
        if days_of_week:
            day_names = [DAY_NAMES[d] for d in sorted(days_of_week)]
            parts.append(f"on {', '.join(day_names)}")
    elif frequency == 'monthly':
        if interval == 1:
            parts.append("Monthly")
        else:
            parts.append(f"Every {interval} months")
        if days_of_month:
            parts.append(f"on day {', '.join(map(str, sorted(days_of_month)))}")
    elif frequency == 'custom':
        parts.append("Custom")
        if days_of_week:
            day_names = [DAY_NAMES[d] for d in sorted(days_of_week)]
            parts.append(f"on {', '.join(day_names)}")
        if days_of_month:
            parts.append(f"on day {', '.join(map(str, sorted(days_of_month)))}")

    parts.append(f"at {time_str}")

    end_date = recurrence.get('end_date')
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            parts.append(f"until {end_dt.strftime('%b %d, %Y')}")
        except ValueError:
            pass

    return ' '.join(parts)
