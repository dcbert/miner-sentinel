"""
Hardware / fleet health alert checks shared by device collectors.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import psycopg2

from notifications.emitter import emit_alert, resolve_open_alerts
from notifications.rules import NotificationRules

logger = logging.getLogger(__name__)


def run_device_health_checks(
    *,
    database_url: str,
    make: str,
    device_db_id: int,
    device_id: str,
    device_name: str,
    temperature_c: Optional[float],
    fan_speed_rpm: Optional[int],
    hashrate_ghs: float,
    expected_hashrate_ghs: Optional[float],
    telegram,
    discord,
    rules: NotificationRules,
    preferences: Optional[dict] = None,
    push=None,
) -> None:
    """Evaluate temp / fan / expected-HR rules after a successful snapshot write."""
    check_temperature(
        database_url=database_url,
        make=make,
        device_db_id=device_db_id,
        device_id=device_id,
        device_name=device_name,
        temperature_c=temperature_c,
        telegram=telegram,
        discord=discord,
        rules=rules,
        preferences=preferences,
        push=push,
    )
    check_fan_dead(
        database_url=database_url,
        make=make,
        device_id=device_id,
        device_name=device_name,
        fan_speed_rpm=fan_speed_rpm,
        hashrate_ghs=hashrate_ghs,
        telegram=telegram,
        discord=discord,
        rules=rules,
        preferences=preferences,
        push=push,
    )
    check_expected_hashrate_drop(
        database_url=database_url,
        make=make,
        device_id=device_id,
        device_name=device_name,
        hashrate_ghs=hashrate_ghs,
        expected_hashrate_ghs=expected_hashrate_ghs,
        telegram=telegram,
        discord=discord,
        rules=rules,
        preferences=preferences,
        push=push,
    )


def check_temperature(
    *,
    database_url: str,
    make: str,
    device_db_id: int,
    device_id: str,
    device_name: str,
    temperature_c: Optional[float],
    telegram,
    discord,
    rules: NotificationRules,
    preferences: Optional[dict] = None,
    push=None,
) -> None:
    if not rules.enabled('temperature_high'):
        return
    if temperature_c is None:
        return

    threshold = float(rules.get('temperature_high', 'threshold_c', 80.0) or 80.0)
    duration = int(rules.get('temperature_high', 'duration_polls', 2) or 2)
    duration = max(1, min(20, duration))

    if temperature_c < threshold:
        resolve_open_alerts(database_url, 'temperature_high', make, device_id)
        return

    # Confirm sustained overheat across recent samples (including current write)
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT temperature_c
            FROM device_hardware_stats
            WHERE device_id = %s AND temperature_c IS NOT NULL
            ORDER BY recorded_at DESC
            LIMIT %s
            """,
            (device_db_id, duration),
        )
        temps = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"temperature check query failed: {e}")
        return

    if len(temps) < duration:
        return
    if not all((t or 0) >= threshold for t in temps):
        return

    emit_alert(
        database_url=database_url,
        event_key='temperature_high',
        method_name='send_temperature_alert',
        telegram=telegram,
        discord=discord,
        rules=rules,
        args=(device_id, device_name, temperature_c, threshold, duration),
        device_make=make,
        device_id=device_id,
        device_name=device_name,
        message=f'{device_name} at {temperature_c:.0f}°C (threshold {threshold:.0f}°C)',
        payload={
            'temperature_c': temperature_c,
            'threshold_c': threshold,
            'duration_polls': duration,
        },
        preferences=preferences,
        push=push,
    )


def check_fan_dead(
    *,
    database_url: str,
    make: str,
    device_id: str,
    device_name: str,
    fan_speed_rpm: Optional[int],
    hashrate_ghs: float,
    telegram,
    discord,
    rules: NotificationRules,
    preferences: Optional[dict] = None,
    push=None,
) -> None:
    if not rules.enabled('fan_dead'):
        return
    # Only alert when actively hashing and fan RPM is known ≈ 0
    if fan_speed_rpm is None:
        return
    if (hashrate_ghs or 0) < 0.1:
        resolve_open_alerts(database_url, 'fan_dead', make, device_id)
        return
    if fan_speed_rpm > 50:
        resolve_open_alerts(database_url, 'fan_dead', make, device_id)
        return

    emit_alert(
        database_url=database_url,
        event_key='fan_dead',
        method_name='send_fan_dead_alert',
        telegram=telegram,
        discord=discord,
        rules=rules,
        args=(device_id, device_name, fan_speed_rpm, hashrate_ghs),
        device_make=make,
        device_id=device_id,
        device_name=device_name,
        message=f'{device_name} fan at {fan_speed_rpm} RPM while hashing {hashrate_ghs:.1f} GH/s',
        payload={'fan_speed_rpm': fan_speed_rpm, 'hashrate_ghs': hashrate_ghs},
        preferences=preferences,
        push=push,
    )


def check_expected_hashrate_drop(
    *,
    database_url: str,
    make: str,
    device_id: str,
    device_name: str,
    hashrate_ghs: float,
    expected_hashrate_ghs: Optional[float],
    telegram,
    discord,
    rules: NotificationRules,
    preferences: Optional[dict] = None,
    push=None,
) -> None:
    if not rules.enabled('expected_hashrate_drop'):
        return
    expected = expected_hashrate_ghs
    if expected is None or expected <= 0:
        return

    drop_pct = float(rules.get('expected_hashrate_drop', 'drop_percent', 30.0) or 30.0)
    floor = expected * (1.0 - drop_pct / 100.0)
    current = hashrate_ghs or 0.0

    if current >= floor:
        resolve_open_alerts(database_url, 'expected_hashrate_drop', make, device_id)
        return

    # Ignore near-zero (offline / restarting) — offline alert covers that
    if current < 0.05:
        return

    actual_drop = ((expected - current) / expected) * 100.0
    emit_alert(
        database_url=database_url,
        event_key='expected_hashrate_drop',
        method_name='send_expected_hashrate_alert',
        telegram=telegram,
        discord=discord,
        rules=rules,
        args=(device_id, device_name, current, expected, actual_drop),
        device_make=make,
        device_id=device_id,
        device_name=device_name,
        message=(
            f'{device_name} hashrate {current:.1f} GH/s '
            f'({actual_drop:.0f}% below expected {expected:.1f} GH/s)'
        ),
        payload={
            'hashrate_ghs': current,
            'expected_hashrate_ghs': expected,
            'drop_percent': actual_drop,
            'threshold_percent': drop_pct,
        },
        preferences=preferences,
        push=push,
    )


def check_pool_staleness(
    *,
    database_url: str,
    telegram,
    discord,
    rules: NotificationRules,
    preferences: Optional[dict] = None,
    pool_type: str = '',
    force_failure: bool = False,
    error_message: str = '',
    push=None,
) -> None:
    """Alert when pool collector fails or latest pool_stats is older than threshold."""
    if not rules.enabled('pool_down'):
        return

    stale_minutes = int(rules.get('pool_down', 'stale_minutes', 30) or 30)
    stale_minutes = max(5, min(1440, stale_minutes))

    should_alert = force_failure
    latest_at = None
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        if pool_type:
            cursor.execute(
                """
                SELECT recorded_at
                FROM pool_stats
                WHERE pool_type = %s
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (pool_type,),
            )
        else:
            cursor.execute(
                """
                SELECT recorded_at
                FROM pool_stats
                ORDER BY recorded_at DESC
                LIMIT 1
                """
            )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            latest_at = row[0]
            from datetime import datetime, timezone, timedelta
            ts = latest_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - ts
            if age > timedelta(minutes=stale_minutes):
                should_alert = True
        elif force_failure:
            should_alert = True
    except Exception as e:
        logger.error(f"pool staleness check failed: {e}")
        should_alert = True
        error_message = error_message or str(e)

    if not should_alert:
        resolve_open_alerts(database_url, 'pool_down')
        return

    age_note = ''
    if latest_at:
        age_note = f'; last sample {latest_at}'
    emit_alert(
        database_url=database_url,
        event_key='pool_down',
        method_name='send_pool_down_alert',
        telegram=telegram,
        discord=discord,
        rules=rules,
        args=(pool_type or 'pool', error_message or f'No fresh stats for {stale_minutes}+ minutes'),
        device_make='',
        device_id='',
        device_name='',
        message=f'Pool stats unavailable{age_note}',
        payload={
            'pool_type': pool_type,
            'stale_minutes': stale_minutes,
            'error': error_message,
            'latest_at': latest_at.isoformat() if latest_at else None,
        },
        preferences=preferences,
        push=push,
    )
