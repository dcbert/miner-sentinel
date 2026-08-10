"""
Parse hours / days / from / to query params into a single query window.

Used by overview, analytics, pool, and device history endpoints so the global
UI time range maps to one coherent filter (including absolute custom ranges).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from math import ceil
from typing import Any, Mapping, Optional, Tuple

from django.utils import timezone
from django.utils.dateparse import parse_datetime

# Cap query windows to protect large installs (matches fleet endpoints: 90 days)
MAX_HOURS = 24 * 90
MAX_DAYS = 90
DEFAULT_HOURS = 24


@dataclass(frozen=True)
class TimeWindow:
    """Resolved absolute window plus duration metadata for API responses."""

    start: datetime
    end: datetime
    hours: int
    days: int

    def as_filter(self) -> dict:
        """Kwargs for Django ORM ``recorded_at`` filters."""
        return {
            'recorded_at__gte': self.start,
            'recorded_at__lte': self.end,
        }


def parse_int_param(
    value: Any,
    default: int,
    min_value: int = 1,
    max_value: Optional[int] = None,
) -> int:
    """Safely parse a positive integer query param with optional bounds."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < min_value:
        n = min_value
    if max_value is not None and n > max_value:
        n = max_value
    return n


def _ensure_aware(dt: datetime) -> datetime:
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == '':
        return None
    text = str(value).strip()
    if not text:
        return None
    # Support trailing Z
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    dt = parse_datetime(text)
    if dt is None:
        try:
            dt = datetime.fromisoformat(text)
        except (TypeError, ValueError):
            return None
    return _ensure_aware(dt)


def _duration_parts(start: datetime, end: datetime, max_hours: int, max_days: int) -> Tuple[int, int]:
    """Derive hours/days from an absolute span without float-ceil noise.

    Sub-second differences (dual ``now()`` calls, ISO round-trips) must not
    bump an exact N-hour window to N+1.
    """
    raw_seconds = max(0.0, (end - start).total_seconds())
    # Round to nearest second, then integer-ceil to whole hours
    whole_seconds = int(raw_seconds + 0.5)
    hours = max(1, min(max_hours, (whole_seconds + 3599) // 3600))
    days = max(1, min(max_days, (hours + 23) // 24))
    return hours, days


def parse_time_window(
    params: Mapping[str, Any],
    *,
    default_hours: int = DEFAULT_HOURS,
    max_hours: int = MAX_HOURS,
    max_days: int = MAX_DAYS,
    now: Optional[datetime] = None,
) -> TimeWindow:
    """
    Resolve a single time window from request query params.

    Preference order:
    1. Absolute ``from`` + ``to`` (ISO-8601), duration clamped to ``max_hours``
    2. Relative ``hours`` ending at now
    3. Relative ``days`` ending at now (when hours absent)
    4. ``default_hours``

    ``days`` is always derived from the effective hour span so sub-day presets
    (1h, 6h) do not silently expand period aggregates to a full day.
    """
    now = now or timezone.now()
    if timezone.is_naive(now):
        now = timezone.make_aware(now, dt_timezone.utc)

    from_raw = params.get('from')
    to_raw = params.get('to')
    start = _parse_iso_datetime(from_raw)
    end = _parse_iso_datetime(to_raw)

    if start is not None and end is not None and end > start:
        max_delta = timedelta(hours=max_hours)
        if end - start > max_delta:
            start = end - max_delta
        hours, days = _duration_parts(start, end, max_hours, max_days)
        return TimeWindow(start=start, end=end, hours=hours, days=days)

    hours_raw = params.get('hours')
    days_raw = params.get('days')

    has_hours = hours_raw is not None and str(hours_raw).strip() != ''
    has_days = days_raw is not None and str(days_raw).strip() != ''

    if has_hours:
        hours = parse_int_param(hours_raw, default_hours, min_value=1, max_value=max_hours)
    elif has_days:
        day_count = parse_int_param(days_raw, max(1, default_hours // 24), min_value=1, max_value=max_days)
        hours = min(max_hours, day_count * 24)
    else:
        hours = max(1, min(max_hours, default_hours))

    days = max(1, min(max_days, int(ceil(hours / 24.0))))
    end = now
    start = end - timedelta(hours=hours)
    return TimeWindow(start=start, end=end, hours=hours, days=days)
