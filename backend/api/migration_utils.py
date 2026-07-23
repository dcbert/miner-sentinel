"""
Helpers for migrating legacy per-vendor tables into unified devices/pool tables.

Used by migration 0012 and by unit tests. Keep logic stable once shipped.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, Optional, Tuple


def convert_hashrate_str_to_ghs(hashrate_str: Any) -> Optional[float]:
    """Convert hashrate string (e.g. '466G', '1.29T', '185M') to GH/s."""
    if hashrate_str is None or hashrate_str == '':
        return None
    if isinstance(hashrate_str, (int, float)):
        return float(hashrate_str)

    hashrate_str = str(hashrate_str).strip()
    match = re.match(r'([\d.]+)\s*([KMGTP]?)', hashrate_str, re.IGNORECASE)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {
        '': 1e-9,
        'K': 1e-6,
        'M': 0.001,
        'G': 1.0,
        'T': 1000.0,
        'P': 1_000_000.0,
    }
    return value * multipliers.get(unit, 1.0)


def bitaxe_system_to_details(row) -> Dict[str, Any]:
    """Pack Bitaxe-only system fields into details JSON."""
    keys = [
        'asic_model', 'board_version', 'version', 'axe_os_version', 'idf_version',
        'running_partition', 'wifi_status', 'core_voltage', 'core_voltage_actual',
        'pool_difficulty', 'small_core_count', 'vr_temp', 'temp_target', 'overheat_mode',
        'auto_fan_speed', 'fan_speed_percent', 'min_fan_speed', 'max_power',
        'nominal_voltage', 'overclock_enabled', 'display_type', 'display_rotation',
        'invert_screen', 'display_timeout', 'stratum_port', 'fallback_stratum_port',
        'free_heap', 'is_psram_available',
    ]
    details = {}
    for key in keys:
        val = getattr(row, key, None)
        if val is not None:
            details[key] = val
    return details


def avalon_system_to_details(row) -> Dict[str, Any]:
    """Pack Avalon-only system fields into details JSON."""
    details = {}
    for key in (
        'hardware_version', 'memory_usage_percent', 'storage_usage_percent',
        'target_frequency', 'target_voltage', 'auto_tune_enabled',
        'backup_pool_url', 'backup_pool_user', 'active_pool',
        'system_uptime_seconds',
    ):
        val = getattr(row, key, None)
        if val is not None:
            details[key] = val
    return details


def unix_to_datetime(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=dt_timezone.utc)
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def migrate_legacy_to_unified(apps, schema_editor, batch_size: int = 2000) -> Dict[str, int]:
    """
    Copy all legacy device/pool rows into unified tables.
    Idempotent when target tables already hold a full copy (skips if counts match).
    Returns counts written (or already present).
    """
    Device = apps.get_model('api', 'Device')
    DeviceMiningStats = apps.get_model('api', 'DeviceMiningStats')
    DeviceHardwareStats = apps.get_model('api', 'DeviceHardwareStats')
    DeviceSystemInfo = apps.get_model('api', 'DeviceSystemInfo')
    PoolStats = apps.get_model('api', 'PoolStats')

    BitAxeDevice = apps.get_model('api', 'BitAxeDevice')
    BitAxeMiningStats = apps.get_model('api', 'BitAxeMiningStats')
    BitAxeHardwareLog = apps.get_model('api', 'BitAxeHardwareLog')
    BitAxeSystemInfo = apps.get_model('api', 'BitAxeSystemInfo')
    BitAxePoolStats = apps.get_model('api', 'BitAxePoolStats')

    AvalonDevice = apps.get_model('api', 'AvalonDevice')
    AvalonMiningStats = apps.get_model('api', 'AvalonMiningStats')
    AvalonHardwareLogs = apps.get_model('api', 'AvalonHardwareLogs')
    AvalonSystemInfo = apps.get_model('api', 'AvalonSystemInfo')
    CollectorSettings = apps.get_model('api', 'CollectorSettings')

    expected_devices = BitAxeDevice.objects.count() + AvalonDevice.objects.count()
    expected_mining = BitAxeMiningStats.objects.count() + AvalonMiningStats.objects.count()
    expected_hardware = BitAxeHardwareLog.objects.count() + AvalonHardwareLogs.objects.count()
    expected_system = BitAxeSystemInfo.objects.count() + AvalonSystemInfo.objects.count()
    expected_pool = BitAxePoolStats.objects.count()

    # Idempotent short-circuit: full copy already present
    if (
        Device.objects.count() == expected_devices
        and DeviceMiningStats.objects.count() == expected_mining
        and DeviceHardwareStats.objects.count() == expected_hardware
        and DeviceSystemInfo.objects.count() == expected_system
        and PoolStats.objects.count() == expected_pool
        and expected_devices + expected_mining + expected_hardware + expected_system + expected_pool > 0
    ):
        return {
            'devices': expected_devices,
            'mining': expected_mining,
            'hardware': expected_hardware,
            'system': expected_system,
            'pool': expected_pool,
            'skipped': 1,
        }

    # If partially populated, clear unified tables and re-copy (safe: legacy untouched)
    if Device.objects.exists() or PoolStats.objects.exists():
        DeviceMiningStats.objects.all().delete()
        DeviceHardwareStats.objects.all().delete()
        DeviceSystemInfo.objects.all().delete()
        Device.objects.all().delete()
        PoolStats.objects.all().delete()

    device_map: Dict[Tuple[str, int], int] = {}  # (make, old_pk) -> new id

    # --- Devices ---
    for row in BitAxeDevice.objects.all().iterator(chunk_size=batch_size):
        obj = Device.objects.create(
            device_id=row.device_id,
            name=row.device_name,
            make='bitaxe',
            model=None,
            protocol='http_axeos',
            ip_address=row.ip_address,
            port=None,
            is_active=row.is_active,
            last_seen_at=row.last_seen_at,
            error_message=row.error_message,
            connection_config={},
            created_at=row.created_at,
        )
        device_map[('bitaxe', row.id)] = obj.id

    for row in AvalonDevice.objects.all().iterator(chunk_size=batch_size):
        obj = Device.objects.create(
            device_id=row.device_id,
            name=row.device_name,
            make='avalon',
            model=None,
            protocol='cgminer_tcp',
            ip_address=row.ip_address,
            port=4028,
            is_active=row.is_active,
            last_seen_at=row.last_seen_at,
            error_message=row.error_message,
            connection_config={},
            created_at=row.created_at,
        )
        device_map[('avalon', row.id)] = obj.id

    # --- Mining (Bitaxe) ---
    batch = []
    for row in BitAxeMiningStats.objects.all().iterator(chunk_size=batch_size):
        new_id = device_map.get(('bitaxe', row.device_id))
        if not new_id:
            continue
        batch.append(DeviceMiningStats(
            device_id=new_id,
            recorded_at=row.recorded_at,
            hashrate_ghs=row.hashrate_ghs or 0.0,
            hashrate_avg_ghs=None,
            shares_accepted=row.shares_accepted or 0,
            shares_rejected=row.shares_rejected or 0,
            hardware_errors=None,
            blocks_found=row.blocks_found or 0,
            uptime_seconds=row.uptime_seconds or 0,
            best_difficulty=float(row.best_difficulty) if row.best_difficulty is not None else None,
            best_session_difficulty=(
                float(row.best_session_difficulty) if row.best_session_difficulty is not None else None
            ),
            pool_url=row.pool_url,
            pool_user=row.pool_user,
            created_at=row.created_at,
        ))
        if len(batch) >= batch_size:
            DeviceMiningStats.objects.bulk_create(batch)
            batch = []
    if batch:
        DeviceMiningStats.objects.bulk_create(batch)

    # --- Mining (Avalon) ---
    batch = []
    for row in AvalonMiningStats.objects.all().iterator(chunk_size=batch_size):
        new_id = device_map.get(('avalon', row.device_id))
        if not new_id:
            continue
        batch.append(DeviceMiningStats(
            device_id=new_id,
            recorded_at=row.recorded_at,
            hashrate_ghs=row.hashrate_ghs or 0.0,
            hashrate_avg_ghs=None,
            shares_accepted=row.shares_accepted or 0,
            shares_rejected=row.shares_rejected or 0,
            hardware_errors=None,
            blocks_found=row.blocks_found or 0,
            uptime_seconds=row.uptime_seconds or 0,
            best_difficulty=float(row.difficulty) if row.difficulty is not None else None,
            best_session_difficulty=None,
            pool_url=row.pool_url,
            pool_user=row.pool_user,
            created_at=row.created_at,
        ))
        if len(batch) >= batch_size:
            DeviceMiningStats.objects.bulk_create(batch)
            batch = []
    if batch:
        DeviceMiningStats.objects.bulk_create(batch)

    # --- Hardware (Bitaxe) ---
    batch = []
    for row in BitAxeHardwareLog.objects.all().iterator(chunk_size=batch_size):
        new_id = device_map.get(('bitaxe', row.device_id))
        if not new_id:
            continue
        batch.append(DeviceHardwareStats(
            device_id=new_id,
            recorded_at=row.recorded_at,
            temperature_c=row.temperature_c,
            temperature_board_c=None,
            temperature_chip_c=None,
            power_watts=row.power_watts,
            efficiency_j_per_th=row.efficiency_j_per_th,
            fan_speed_rpm=row.fan_speed_rpm,
            fan_speed_percent=None,
            voltage=row.voltage,
            frequency_mhz=float(row.frequency_mhz) if row.frequency_mhz is not None else None,
            created_at=row.created_at,
        ))
        if len(batch) >= batch_size:
            DeviceHardwareStats.objects.bulk_create(batch)
            batch = []
    if batch:
        DeviceHardwareStats.objects.bulk_create(batch)

    # --- Hardware (Avalon) ---
    batch = []
    for row in AvalonHardwareLogs.objects.all().iterator(chunk_size=batch_size):
        new_id = device_map.get(('avalon', row.device_id))
        if not new_id:
            continue
        batch.append(DeviceHardwareStats(
            device_id=new_id,
            recorded_at=row.recorded_at,
            temperature_c=row.temperature_c,
            temperature_board_c=None,
            temperature_chip_c=None,
            power_watts=row.power_watts,
            efficiency_j_per_th=row.efficiency_j_per_th,
            fan_speed_rpm=row.fan_speed_rpm,
            fan_speed_percent=None,
            voltage=row.voltage,
            frequency_mhz=float(row.frequency_mhz) if row.frequency_mhz is not None else None,
            created_at=row.created_at,
        ))
        if len(batch) >= batch_size:
            DeviceHardwareStats.objects.bulk_create(batch)
            batch = []
    if batch:
        DeviceHardwareStats.objects.bulk_create(batch)

    # --- System (Bitaxe) ---
    batch = []
    for row in BitAxeSystemInfo.objects.all().iterator(chunk_size=batch_size):
        new_id = device_map.get(('bitaxe', row.device_id))
        if not new_id:
            continue
        details = bitaxe_system_to_details(row)
        batch.append(DeviceSystemInfo(
            device_id=new_id,
            recorded_at=row.recorded_at,
            hostname=row.hostname,
            mac_address=row.mac_address,
            firmware_version=row.version or row.axe_os_version,
            serial_number=None,
            model_reported=row.asic_model,
            expected_hashrate_ghs=row.expected_hashrate,
            primary_pool_url=row.stratum_url,
            primary_pool_user=row.stratum_user,
            fallback_pool_url=row.fallback_stratum_url,
            fallback_pool_user=None,
            using_fallback_pool=row.is_using_fallback,
            wifi_ssid=row.ssid,
            wifi_rssi=row.wifi_rssi,
            details=details,
            created_at=row.created_at,
        ))
        if len(batch) >= batch_size:
            DeviceSystemInfo.objects.bulk_create(batch)
            batch = []
    if batch:
        DeviceSystemInfo.objects.bulk_create(batch)

    # --- System (Avalon) ---
    batch = []
    for row in AvalonSystemInfo.objects.all().iterator(chunk_size=batch_size):
        new_id = device_map.get(('avalon', row.device_id))
        if not new_id:
            continue
        details = avalon_system_to_details(row)
        batch.append(DeviceSystemInfo(
            device_id=new_id,
            recorded_at=row.recorded_at,
            hostname=row.hostname,
            mac_address=row.mac_address,
            firmware_version=row.firmware_version,
            serial_number=row.serial_number,
            model_reported=row.device_model,
            expected_hashrate_ghs=None,
            primary_pool_url=row.primary_pool_url,
            primary_pool_user=row.primary_pool_user,
            fallback_pool_url=row.backup_pool_url,
            fallback_pool_user=row.backup_pool_user,
            using_fallback_pool=None,
            wifi_ssid=row.wifi_ssid,
            wifi_rssi=row.wifi_signal_strength,
            details=details,
            created_at=row.created_at,
        ))
        if len(batch) >= batch_size:
            DeviceSystemInfo.objects.bulk_create(batch)
            batch = []
    if batch:
        DeviceSystemInfo.objects.bulk_create(batch)

    # --- Pool stats ---
    pool_type = 'ckpool'
    try:
        settings_row = CollectorSettings.objects.filter(pk=1).first()
        if settings_row and getattr(settings_row, 'pool_type', None):
            pool_type = settings_row.pool_type
    except Exception:
        pool_type = 'ckpool'

    batch = []
    for row in BitAxePoolStats.objects.all().iterator(chunk_size=batch_size):
        h1m = row.hashrate_1m_ghs
        if h1m is None:
            h1m = convert_hashrate_str_to_ghs(row.hashrate_1m)
        h5m = convert_hashrate_str_to_ghs(row.hashrate_5m)
        h1h = convert_hashrate_str_to_ghs(row.hashrate_1hr)
        h1d = row.hashrate_1d_ghs
        if h1d is None:
            h1d = convert_hashrate_str_to_ghs(row.hashrate_1d)
        h7d = convert_hashrate_str_to_ghs(row.hashrate_7d)

        batch.append(PoolStats(
            pool_type=pool_type,
            pool_address=row.pool_address,
            pool_url=None,
            recorded_at=row.recorded_at,
            hashrate_1m_ghs=h1m,
            hashrate_5m_ghs=h5m,
            hashrate_1h_ghs=h1h,
            hashrate_1d_ghs=h1d,
            hashrate_7d_ghs=h7d,
            hashrate_1m_display=row.hashrate_1m,
            hashrate_5m_display=row.hashrate_5m,
            hashrate_1h_display=row.hashrate_1hr,
            hashrate_1d_display=row.hashrate_1d,
            hashrate_7d_display=row.hashrate_7d,
            workers=row.workers,
            shares=row.shares,
            best_share=float(row.bestshare) if row.bestshare is not None else None,
            best_ever=float(row.bestever) if row.bestever is not None else None,
            last_share_at=unix_to_datetime(row.lastshare),
            last_share_unix=row.lastshare,
            authorised_unix=row.authorised,
            pool_total_miners=None,
            pool_total_hashrate_ghs=None,
            details={'migration_source': 'bitaxe_pool_stats'},
            created_at=row.recorded_at,
        ))
        if len(batch) >= batch_size:
            PoolStats.objects.bulk_create(batch)
            batch = []
    if batch:
        PoolStats.objects.bulk_create(batch)

    # --- Verification ---
    actual = {
        'devices': Device.objects.count(),
        'mining': DeviceMiningStats.objects.count(),
        'hardware': DeviceHardwareStats.objects.count(),
        'system': DeviceSystemInfo.objects.count(),
        'pool': PoolStats.objects.count(),
    }
    expected = {
        'devices': expected_devices,
        'mining': expected_mining,
        'hardware': expected_hardware,
        'system': expected_system,
        'pool': expected_pool,
    }
    mismatches = {k: (expected[k], actual[k]) for k in expected if expected[k] != actual[k]}
    if mismatches:
        raise RuntimeError(
            f"Unified data migration verification failed: {mismatches}. "
            "Legacy tables were not modified."
        )

    return actual


def reverse_unified_data(apps, schema_editor):
    """Remove unified table rows only; leave legacy tables intact."""
    Device = apps.get_model('api', 'Device')
    DeviceMiningStats = apps.get_model('api', 'DeviceMiningStats')
    DeviceHardwareStats = apps.get_model('api', 'DeviceHardwareStats')
    DeviceSystemInfo = apps.get_model('api', 'DeviceSystemInfo')
    PoolStats = apps.get_model('api', 'PoolStats')

    DeviceMiningStats.objects.all().delete()
    DeviceHardwareStats.objects.all().delete()
    DeviceSystemInfo.objects.all().delete()
    Device.objects.all().delete()
    PoolStats.objects.all().delete()


def verify_unification_counts(apps_or_models=None) -> Dict[str, Any]:
    """
    Compare legacy vs unified counts.
    Can be called with Django apps registry (historical models) or live models.
    """
    if apps_or_models is None:
        from api import models as m

        legacy_devices = m.BitAxeDevice.objects.count() + m.AvalonDevice.objects.count()
        legacy_mining = m.BitAxeMiningStats.objects.count() + m.AvalonMiningStats.objects.count()
        legacy_hardware = m.BitAxeHardwareLog.objects.count() + m.AvalonHardwareLogs.objects.count()
        legacy_system = m.BitAxeSystemInfo.objects.count() + m.AvalonSystemInfo.objects.count()
        legacy_pool = m.BitAxePoolStats.objects.count()

        unified_devices = m.Device.objects.count()
        unified_mining = m.DeviceMiningStats.objects.count()
        unified_hardware = m.DeviceHardwareStats.objects.count()
        unified_system = m.DeviceSystemInfo.objects.count()
        unified_pool = m.PoolStats.objects.count()
    else:
        raise NotImplementedError("Pass None to use live models")

    checks = {
        'devices': (legacy_devices, unified_devices),
        'mining': (legacy_mining, unified_mining),
        'hardware': (legacy_hardware, unified_hardware),
        'system': (legacy_system, unified_system),
        'pool': (legacy_pool, unified_pool),
    }
    ok = all(a == b for a, b in checks.values())
    return {'ok': ok, 'checks': checks}
