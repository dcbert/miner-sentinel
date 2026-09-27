"""
Central alert emit path: persist AlertEvent + fan-out to Telegram/Discord/push.

Collectors and control actions should call emit_alert() so the Activity feed
and chat channels stay in sync.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import psycopg2
from psycopg2.extras import Json

from notifications.rules import NotificationRules

logger = logging.getLogger(__name__)

DEFAULT_PREFERENCES = {
    'quiet_hours_enabled': False,
    'quiet_hours_start': '22:00',
    'quiet_hours_end': '07:00',
    'alert_repeat_minutes': 60,
}

EVENT_TITLES = {
    'device_offline': 'Device offline',
    'device_online': 'Device online',
    'hashrate_stagnation': 'Hashrate stagnation',
    'auto_restart': 'Auto-restart',
    'best_difficulty': 'New best difficulty',
    'temperature_high': 'High temperature',
    'fan_dead': 'Fan not spinning',
    'pool_down': 'Pool unavailable',
    'collector_down': 'Collector unhealthy',
    'expected_hashrate_drop': 'Hashrate drop',
}

# Celebrations / news — never stay as "open problems" (auto-acknowledged on create)
HIGHLIGHT_EVENT_TYPES = frozenset({
    'best_difficulty',
    'device_online',
})


def is_highlight_event(event_key: str, severity: str = '') -> bool:
    if event_key in HIGHLIGHT_EVENT_TYPES:
        return True
    if (event_key or '').startswith('user_'):
        return True
    return severity == 'info' and event_key not in (
        'device_offline',
        'hashrate_stagnation',
        'auto_restart',
        'temperature_high',
        'fan_dead',
        'pool_down',
        'collector_down',
        'expected_hashrate_drop',
    )


def fingerprint_for(
    event_key: str,
    device_make: str = '',
    device_id: str = '',
) -> str:
    make = (device_make or '').strip()
    key = (device_id or '').strip()
    if make or key:
        return f"{event_key}:{make}:{key}"[:191]
    return event_key[:191]


def _parse_hhmm(value: str) -> Optional[Tuple[int, int]]:
    try:
        parts = (value or '').strip().split(':')
        return int(parts[0]), int(parts[1])
    except (TypeError, ValueError, IndexError):
        return None


def in_quiet_hours(prefs: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    if not prefs.get('quiet_hours_enabled'):
        return False
    start = _parse_hhmm(prefs.get('quiet_hours_start') or '22:00')
    end = _parse_hhmm(prefs.get('quiet_hours_end') or '07:00')
    if not start or not end:
        return False
    now = now or datetime.now().astimezone()
    minutes = now.hour * 60 + now.minute
    start_m = start[0] * 60 + start[1]
    end_m = end[0] * 60 + end[1]
    if start_m == end_m:
        return False
    if start_m < end_m:
        return start_m <= minutes < end_m
    # Overnight window (e.g. 22:00–07:00)
    return minutes >= start_m or minutes < end_m


def _format_difficulty(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    if n >= 1e12:
        return f'{n / 1e12:.2f}T'
    if n >= 1e9:
        return f'{n / 1e9:.2f}G'
    if n >= 1e6:
        return f'{n / 1e6:.2f}M'
    if n >= 1e3:
        return f'{n / 1e3:.2f}K'
    return f'{n:.0f}'


def _default_message(event_key: str, device_name: str, args: tuple) -> str:
    name = device_name or (args[1] if len(args) > 1 else args[0] if args else 'fleet')
    # send_best_difficulty_alert(device_id, device_name, new_best, previous_best)
    if event_key == 'best_difficulty' and len(args) >= 3:
        return f'{name} set a new best share · {_format_difficulty(args[2])}'
    templates = {
        'device_offline': f'{name} went offline',
        'device_online': f'{name} is back online',
        'hashrate_stagnation': f'{name} hashrate stagnation',
        'auto_restart': f'{name} auto-restart triggered',
        'best_difficulty': f'{name} set a new best share',
        'temperature_high': f'{name} temperature above threshold',
        'fan_dead': f'{name} fan not spinning while hashing',
        'pool_down': 'Pool statistics unavailable',
        'collector_down': 'Data collector unhealthy',
        'expected_hashrate_drop': f'{name} hashrate below expected',
    }
    return templates.get(event_key, f'{event_key}: {name}')


def _lookup_device_pk(cursor, device_make: str, device_id: str) -> Optional[int]:
    if not device_make or not device_id:
        return None
    cursor.execute(
        "SELECT id FROM devices WHERE make = %s AND device_id = %s LIMIT 1",
        (device_make, device_id),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def resolve_open_alerts(
    database_url: str,
    event_key: str,
    device_make: str = '',
    device_id: str = '',
) -> int:
    """Mark open alerts with matching fingerprint as resolved."""
    fp = fingerprint_for(event_key, device_make, device_id)
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET resolved_at = %s
            WHERE fingerprint = %s
              AND resolved_at IS NULL
            """,
            (datetime.now(timezone.utc), fp),
        )
        count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        if count:
            logger.info(f"Resolved {count} open alert(s) for {fp}")
        return count
    except Exception as e:
        logger.error(f"Failed to resolve alerts for {fp}: {e}")
        return 0


def emit_alert(
    *,
    database_url: str,
    event_key: str,
    method_name: str,
    telegram,
    discord,
    rules: NotificationRules,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    device_make: str = '',
    device_id: str = '',
    device_name: str = '',
    message: Optional[str] = None,
    severity: Optional[str] = None,
    payload: Optional[dict] = None,
    preferences: Optional[dict] = None,
    push=None,
) -> Optional[int]:
    """
    Persist an AlertEvent and optionally deliver to chat / push channels.

    Returns the alert_events.id when persisted, else None.
    """
    kwargs = kwargs or {}
    prefs = {**DEFAULT_PREFERENCES, **(preferences or {})}

    if not rules.enabled(event_key):
        logger.debug(f"Notification skipped ({event_key} disabled)")
        return None

    sev = severity or rules.severity(event_key, 'warn')
    if sev not in ('info', 'warn', 'critical'):
        sev = 'warn'

    # Prefer explicit ids; fall back to common notifier arg order (id, name, ...)
    did = device_id or (str(args[0]) if args else '')
    dname = device_name or (str(args[1]) if len(args) > 1 else did)
    msg = message or _default_message(event_key, dname, args)
    fp = fingerprint_for(event_key, device_make, did)
    now = datetime.now(timezone.utc)
    payload = dict(payload or {})

    alert_id = None
    should_chat = True
    muted = False

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        device_pk = _lookup_device_pk(cursor, device_make, did)

        # Find latest open (unresolved) alert with same fingerprint
        cursor.execute(
            """
            SELECT id, muted_until, last_notified_at, acknowledged_at
            FROM alert_events
            WHERE fingerprint = %s AND resolved_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (fp,),
        )
        existing = cursor.fetchone()
        highlight = is_highlight_event(event_key, sev)

        if existing and not highlight:
            alert_id, muted_until, last_notified_at, acknowledged_at = existing
            if muted_until and muted_until.replace(tzinfo=timezone.utc) > now:
                muted = True
                should_chat = False
            # Update message/payload on open event; keep acknowledged state
            cursor.execute(
                """
                UPDATE alert_events
                SET message = %s, payload = %s, severity = %s
                WHERE id = %s
                """,
                (msg, Json(payload), sev, alert_id),
            )
            # Re-alert cadence
            repeat_min = int(prefs.get('alert_repeat_minutes') or 60)
            if last_notified_at:
                ln = last_notified_at
                if ln.tzinfo is None:
                    ln = ln.replace(tzinfo=timezone.utc)
                if now - ln < timedelta(minutes=max(1, repeat_min)):
                    should_chat = False
            # Already acknowledged: stay in journal but don't re-spam chat
            if acknowledged_at:
                should_chat = False
        else:
            # Highlights always get a fresh journal row; close any prior twin.
            # Problems insert when no open fingerprint match.
            if highlight:
                cursor.execute(
                    """
                    UPDATE alert_events
                    SET acknowledged_at = COALESCE(acknowledged_at, %s),
                        resolved_at = COALESCE(resolved_at, %s)
                    WHERE fingerprint = %s AND resolved_at IS NULL
                    """,
                    (now, now, fp),
                )
            # Highlights are news, not tasks — acknowledge immediately.
            ack_at = now if highlight else None
            cursor.execute(
                """
                INSERT INTO alert_events (
                    event_type, severity, device_id, device_make, device_key,
                    device_name, message, payload, fingerprint, created_at,
                    acknowledged_at, last_notified_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL
                )
                RETURNING id
                """,
                (
                    event_key,
                    sev,
                    device_pk,
                    device_make or '',
                    did or '',
                    dname or '',
                    msg,
                    Json(payload),
                    fp,
                    now,
                    ack_at,
                ),
            )
            alert_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to persist AlertEvent ({event_key}): {e}", exc_info=True)
        # Still attempt chat so outages aren't silent if DB write fails
        alert_id = None

    # Quiet hours: suppress non-critical chat
    if should_chat and sev != 'critical' and in_quiet_hours(prefs):
        logger.debug(f"Quiet hours: skipping chat for {event_key}")
        should_chat = False

    if muted:
        logger.debug(f"Alert muted until further notice: {fp}")

    if should_chat:
        try:
            tg = getattr(telegram, method_name, None) if telegram is not None else None
            dc = getattr(discord, method_name, None) if discord is not None else None
            if tg:
                tg(*args, **kwargs)
            if dc:
                dc(*args, **kwargs)
            if push is not None and getattr(push, 'enabled', False):
                title = EVENT_TITLES.get(event_key, event_key.replace('_', ' ').title())
                push.deliver(
                    title=title,
                    message=msg,
                    severity=sev,
                    event_key=event_key,
                )
            if alert_id and database_url:
                try:
                    conn = psycopg2.connect(database_url)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE alert_events SET last_notified_at = %s WHERE id = %s",
                        (now, alert_id),
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Could not update last_notified_at: {e}")
        except Exception as e:
            logger.error(f"Chat fan-out failed for {event_key}: {e}", exc_info=True)

    return alert_id
