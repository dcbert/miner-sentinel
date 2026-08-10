"""
Normalized snapshots and dual-write persistence for multi-make miners and pools.

Adapters fill these dataclasses in canonical units; writers own SQL.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)


@dataclass
class MiningMetrics:
    hashrate_ghs: float = 0.0
    hashrate_avg_ghs: Optional[float] = None
    shares_accepted: int = 0
    shares_rejected: int = 0
    hardware_errors: Optional[int] = None
    blocks_found: int = 0
    uptime_seconds: int = 0
    best_difficulty: Optional[float] = None
    best_session_difficulty: Optional[float] = None
    pool_url: Optional[str] = None
    pool_user: Optional[str] = None


@dataclass
class HardwareMetrics:
    temperature_c: Optional[float] = None
    temperature_board_c: Optional[float] = None
    temperature_chip_c: Optional[float] = None
    power_watts: Optional[float] = None
    efficiency_j_per_th: Optional[float] = None
    fan_speed_rpm: Optional[int] = None
    fan_speed_percent: Optional[int] = None
    voltage: Optional[float] = None
    frequency_mhz: Optional[float] = None


@dataclass
class SystemMetrics:
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    serial_number: Optional[str] = None
    model_reported: Optional[str] = None
    expected_hashrate_ghs: Optional[float] = None
    primary_pool_url: Optional[str] = None
    primary_pool_user: Optional[str] = None
    fallback_pool_url: Optional[str] = None
    fallback_pool_user: Optional[str] = None
    using_fallback_pool: Optional[bool] = None
    wifi_ssid: Optional[str] = None
    wifi_rssi: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedDeviceSnapshot:
    make: str
    device_id: str
    recorded_at: datetime
    online: bool
    error_message: Optional[str] = None
    mining: Optional[MiningMetrics] = None
    hardware: Optional[HardwareMetrics] = None
    system: Optional[SystemMetrics] = None


@dataclass
class NormalizedPoolSnapshot:
    pool_type: str
    pool_address: str
    recorded_at: datetime
    pool_url: Optional[str] = None
    hashrate_1m_ghs: Optional[float] = None
    hashrate_5m_ghs: Optional[float] = None
    hashrate_1h_ghs: Optional[float] = None
    hashrate_1d_ghs: Optional[float] = None
    hashrate_7d_ghs: Optional[float] = None
    hashrate_1m_display: Optional[str] = None
    hashrate_5m_display: Optional[str] = None
    hashrate_1h_display: Optional[str] = None
    hashrate_1d_display: Optional[str] = None
    hashrate_7d_display: Optional[str] = None
    workers: Optional[int] = None
    shares: Optional[int] = None
    best_share: Optional[float] = None
    best_ever: Optional[float] = None
    last_share_unix: Optional[int] = None
    authorised_unix: Optional[int] = None
    pool_total_miners: Optional[int] = None
    pool_total_hashrate_ghs: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


def efficiency_j_per_th(power_watts: Optional[float], hashrate_ghs: Optional[float]) -> Optional[float]:
    if not power_watts or not hashrate_ghs or hashrate_ghs <= 0:
        return 0.0 if power_watts is not None else None
    return power_watts / (hashrate_ghs / 1000.0)


def was_device_online(error_message: Optional[str], last_seen_at) -> bool:
    """
    Infer previous online state from registry fields.

    `is_active` means "enabled for collection", not reachability. Online state is
    derived from a successful prior contact (last_seen_at) without an error_message.
    """
    if last_seen_at is None:
        return False
    if error_message is None:
        return True
    return not str(error_message).strip()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeviceDataWriter:
    """Persist normalized device snapshots to unified tables (+ optional legacy dual-write)."""

    def __init__(self, database_url: str, dual_write: bool = False):
        """
        dual_write: when True, also insert into legacy bitaxe_*/avalon_* tables.
        Release B default is False (unified only).
        """
        self.database_url = database_url
        self.dual_write = dual_write

    def get_connection(self):
        return psycopg2.connect(self.database_url)

    def resolve_device_db_id(self, cursor, make: str, device_id: str) -> Optional[int]:
        cursor.execute(
            "SELECT id FROM devices WHERE make = %s AND device_id = %s",
            (make, device_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def resolve_legacy_device_db_id(self, cursor, make: str, device_id: str) -> Optional[int]:
        table = 'bitaxe_devices' if make == 'bitaxe' else 'avalon_devices' if make == 'avalon' else None
        if not table:
            return None
        cursor.execute(f"SELECT id FROM {table} WHERE device_id = %s", (device_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def update_device_status(
        self,
        make: str,
        device_id: str,
        is_online: bool,
        error_message: str = '',
    ) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE devices
                SET last_seen_at = CASE WHEN %s THEN NOW() ELSE last_seen_at END,
                    error_message = %s
                WHERE make = %s AND device_id = %s
                """,
                (is_online, error_message or None, make, device_id),
            )
            if self.dual_write:
                table = 'bitaxe_devices' if make == 'bitaxe' else 'avalon_devices' if make == 'avalon' else None
                if table:
                    cursor.execute(
                        f"""
                        UPDATE {table}
                        SET last_seen_at = CASE WHEN %s THEN NOW() ELSE last_seen_at END,
                            error_message = %s
                        WHERE device_id = %s
                        """,
                        (is_online, error_message or None, device_id),
                    )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update device status for {make}:{device_id}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def write_snapshot(self, snapshot: NormalizedDeviceSnapshot) -> Optional[int]:
        """
        Insert mining/hardware/system rows for an online snapshot.
        Returns unified devices.id or None if device registry row missing.
        """
        if not snapshot.online or not snapshot.mining:
            self.update_device_status(
                snapshot.make,
                snapshot.device_id,
                False,
                snapshot.error_message or '',
            )
            return None

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            device_db_id = self.resolve_device_db_id(cursor, snapshot.make, snapshot.device_id)
            if not device_db_id:
                logger.error(
                    f"Device not found in unified registry: {snapshot.make}:{snapshot.device_id}"
                )
                return None

            # Update last_seen on unified (+ legacy) within this transaction
            cursor.execute(
                """
                UPDATE devices
                SET last_seen_at = NOW(), error_message = NULL
                WHERE id = %s
                """,
                (device_db_id,),
            )
            if self.dual_write:
                table = (
                    'bitaxe_devices' if snapshot.make == 'bitaxe'
                    else 'avalon_devices' if snapshot.make == 'avalon'
                    else None
                )
                if table:
                    cursor.execute(
                        f"""
                        UPDATE {table}
                        SET last_seen_at = NOW(), error_message = NULL
                        WHERE device_id = %s
                        """,
                        (snapshot.device_id,),
                    )

            m = snapshot.mining
            cursor.execute(
                """
                INSERT INTO device_mining_stats (
                    device_id, recorded_at, hashrate_ghs, hashrate_avg_ghs,
                    shares_accepted, shares_rejected, hardware_errors, blocks_found,
                    uptime_seconds, best_difficulty, best_session_difficulty,
                    pool_url, pool_user, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    device_db_id,
                    snapshot.recorded_at,
                    m.hashrate_ghs,
                    m.hashrate_avg_ghs,
                    m.shares_accepted,
                    m.shares_rejected,
                    m.hardware_errors,
                    m.blocks_found,
                    m.uptime_seconds,
                    m.best_difficulty,
                    m.best_session_difficulty,
                    m.pool_url,
                    m.pool_user,
                    snapshot.recorded_at,
                ),
            )

            if snapshot.hardware:
                h = snapshot.hardware
                cursor.execute(
                    """
                    INSERT INTO device_hardware_stats (
                        device_id, recorded_at, temperature_c, temperature_board_c,
                        temperature_chip_c, power_watts, efficiency_j_per_th,
                        fan_speed_rpm, fan_speed_percent, voltage, frequency_mhz, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        device_db_id,
                        snapshot.recorded_at,
                        h.temperature_c,
                        h.temperature_board_c,
                        h.temperature_chip_c,
                        h.power_watts,
                        h.efficiency_j_per_th,
                        h.fan_speed_rpm,
                        h.fan_speed_percent,
                        h.voltage,
                        h.frequency_mhz,
                        snapshot.recorded_at,
                    ),
                )

            if snapshot.system:
                s = snapshot.system
                cursor.execute(
                    """
                    INSERT INTO device_system_info (
                        device_id, recorded_at, hostname, mac_address, firmware_version,
                        serial_number, model_reported, expected_hashrate_ghs,
                        primary_pool_url, primary_pool_user, fallback_pool_url,
                        fallback_pool_user, using_fallback_pool, wifi_ssid, wifi_rssi,
                        details, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        device_db_id,
                        snapshot.recorded_at,
                        s.hostname,
                        s.mac_address,
                        s.firmware_version,
                        s.serial_number,
                        s.model_reported,
                        s.expected_hashrate_ghs,
                        s.primary_pool_url,
                        s.primary_pool_user,
                        s.fallback_pool_url,
                        s.fallback_pool_user,
                        s.using_fallback_pool,
                        s.wifi_ssid,
                        s.wifi_rssi,
                        Json(s.details or {}),
                        snapshot.recorded_at,
                    ),
                )

            if self.dual_write:
                self._dual_write_legacy(cursor, snapshot)

            conn.commit()
            return device_db_id
        except Exception as e:
            conn.rollback()
            logger.error(
                f"Failed to write snapshot for {snapshot.make}:{snapshot.device_id}: {e}",
                exc_info=True,
            )
            raise
        finally:
            cursor.close()
            conn.close()

    def _dual_write_legacy(self, cursor, snapshot: NormalizedDeviceSnapshot) -> None:
        legacy_id = self.resolve_legacy_device_db_id(cursor, snapshot.make, snapshot.device_id)
        if not legacy_id or not snapshot.mining:
            return

        m = snapshot.mining
        h = snapshot.hardware
        s = snapshot.system
        recorded_at = snapshot.recorded_at

        if snapshot.make == 'bitaxe':
            cursor.execute(
                """
                INSERT INTO bitaxe_mining_stats (
                    device_id, recorded_at, hashrate_ghs, shares_accepted,
                    shares_rejected, blocks_found, uptime_seconds,
                    best_difficulty, best_session_difficulty, pool_url, pool_user, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    legacy_id, recorded_at, m.hashrate_ghs, m.shares_accepted,
                    m.shares_rejected, m.blocks_found, m.uptime_seconds,
                    int(m.best_difficulty) if m.best_difficulty is not None else None,
                    int(m.best_session_difficulty) if m.best_session_difficulty is not None else None,
                    m.pool_url, m.pool_user, recorded_at,
                ),
            )
            if h:
                cursor.execute(
                    """
                    INSERT INTO bitaxe_hardware_logs (
                        device_id, recorded_at, power_watts, efficiency_j_per_th,
                        temperature_c, fan_speed_rpm, voltage, frequency_mhz, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        legacy_id, recorded_at, h.power_watts or 0,
                        h.efficiency_j_per_th, h.temperature_c or 0,
                        h.fan_speed_rpm, h.voltage,
                        int(h.frequency_mhz) if h.frequency_mhz is not None else None,
                        recorded_at,
                    ),
                )
            if s:
                d = s.details or {}
                cursor.execute(
                    """
                    INSERT INTO bitaxe_system_info (
                        device_id, recorded_at, asic_model, board_version, hostname, mac_address,
                        version, axe_os_version, idf_version, running_partition,
                        ssid, wifi_status, wifi_rssi,
                        core_voltage, core_voltage_actual, expected_hashrate, pool_difficulty, small_core_count,
                        vr_temp, temp_target, overheat_mode,
                        auto_fan_speed, fan_speed_percent, min_fan_speed,
                        max_power, nominal_voltage, overclock_enabled,
                        display_type, display_rotation, invert_screen, display_timeout,
                        stratum_url, stratum_port, stratum_user, fallback_stratum_url, fallback_stratum_port, is_using_fallback,
                        free_heap, is_psram_available, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        legacy_id, recorded_at,
                        d.get('asic_model') or s.model_reported, d.get('board_version'),
                        s.hostname, s.mac_address,
                        d.get('version') or s.firmware_version, d.get('axe_os_version'),
                        d.get('idf_version'), d.get('running_partition'),
                        s.wifi_ssid, d.get('wifi_status'), s.wifi_rssi,
                        d.get('core_voltage'), d.get('core_voltage_actual'),
                        s.expected_hashrate_ghs, d.get('pool_difficulty'), d.get('small_core_count'),
                        d.get('vr_temp'), d.get('temp_target'), d.get('overheat_mode', 0),
                        d.get('auto_fan_speed', True), d.get('fan_speed_percent'), d.get('min_fan_speed'),
                        d.get('max_power'), d.get('nominal_voltage'), d.get('overclock_enabled', False),
                        d.get('display_type'), d.get('display_rotation', 0), d.get('invert_screen', False),
                        d.get('display_timeout', -1),
                        s.primary_pool_url, d.get('stratum_port'), s.primary_pool_user,
                        s.fallback_pool_url, d.get('fallback_stratum_port'),
                        bool(s.using_fallback_pool) if s.using_fallback_pool is not None else False,
                        d.get('free_heap'), d.get('is_psram_available', False), recorded_at,
                    ),
                )

        elif snapshot.make == 'avalon':
            cursor.execute(
                """
                INSERT INTO avalon_mining_stats (
                    device_id, recorded_at, hashrate_ghs, shares_accepted,
                    shares_rejected, blocks_found, uptime_seconds,
                    difficulty, pool_url, pool_user, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    legacy_id, recorded_at, m.hashrate_ghs, m.shares_accepted,
                    m.shares_rejected, m.blocks_found, m.uptime_seconds,
                    m.best_difficulty or 0.0, m.pool_url, m.pool_user, recorded_at,
                ),
            )
            if h:
                cursor.execute(
                    """
                    INSERT INTO avalon_hardware_logs (
                        device_id, recorded_at, power_watts, efficiency_j_per_th,
                        temperature_c, fan_speed_rpm, voltage, frequency_mhz, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        legacy_id, recorded_at, h.power_watts or 0.0,
                        h.efficiency_j_per_th or 0.0, h.temperature_c or 0.0,
                        h.fan_speed_rpm or 0, h.voltage or 0.0,
                        h.frequency_mhz or 0.0, recorded_at,
                    ),
                )
            if s:
                d = s.details or {}
                cursor.execute(
                    """
                    INSERT INTO avalon_system_info (
                        device_id, recorded_at, device_model, firmware_version, hardware_version,
                        serial_number, mac_address, ip_address, hostname, wifi_ssid, wifi_signal_strength,
                        primary_pool_url, primary_pool_user, backup_pool_url, backup_pool_user, active_pool,
                        system_uptime_seconds, memory_usage_percent, storage_usage_percent,
                        target_frequency, target_voltage, auto_tune_enabled, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    """,
                    (
                        legacy_id, recorded_at, s.model_reported, s.firmware_version,
                        d.get('hardware_version'), s.serial_number, s.mac_address,
                        None, s.hostname, s.wifi_ssid, s.wifi_rssi,
                        s.primary_pool_url, s.primary_pool_user,
                        s.fallback_pool_url or d.get('backup_pool_url'),
                        s.fallback_pool_user or d.get('backup_pool_user'),
                        d.get('active_pool') or s.primary_pool_url,
                        d.get('system_uptime_seconds') or m.uptime_seconds,
                        d.get('memory_usage_percent', 0.0),
                        d.get('storage_usage_percent', 0.0),
                        d.get('target_frequency', 0.0), d.get('target_voltage', 0.0),
                        d.get('auto_tune_enabled', False), recorded_at,
                    ),
                )


class PoolDataWriter:
    """Persist normalized pool snapshots to pool_stats (+ optional legacy dual-write)."""

    def __init__(self, database_url: str, dual_write: bool = False):
        """Release B default: unified pool_stats only."""
        self.database_url = database_url
        self.dual_write = dual_write

    def get_connection(self):
        return psycopg2.connect(self.database_url)

    def write_snapshot(self, snapshot: NormalizedPoolSnapshot) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO pool_stats (
                    pool_type, pool_address, pool_url, recorded_at,
                    hashrate_1m_ghs, hashrate_5m_ghs, hashrate_1h_ghs, hashrate_1d_ghs, hashrate_7d_ghs,
                    hashrate_1m_display, hashrate_5m_display, hashrate_1h_display,
                    hashrate_1d_display, hashrate_7d_display,
                    workers, shares, best_share, best_ever,
                    last_share_at, last_share_unix, authorised_unix,
                    pool_total_miners, pool_total_hashrate_ghs, details, created_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    snapshot.pool_type,
                    snapshot.pool_address,
                    snapshot.pool_url,
                    snapshot.recorded_at,
                    snapshot.hashrate_1m_ghs,
                    snapshot.hashrate_5m_ghs,
                    snapshot.hashrate_1h_ghs,
                    snapshot.hashrate_1d_ghs,
                    snapshot.hashrate_7d_ghs,
                    snapshot.hashrate_1m_display,
                    snapshot.hashrate_5m_display,
                    snapshot.hashrate_1h_display,
                    snapshot.hashrate_1d_display,
                    snapshot.hashrate_7d_display,
                    snapshot.workers,
                    snapshot.shares,
                    snapshot.best_share,
                    snapshot.best_ever,
                    None,
                    snapshot.last_share_unix,
                    snapshot.authorised_unix,
                    snapshot.pool_total_miners,
                    snapshot.pool_total_hashrate_ghs,
                    Json(snapshot.details or {}),
                    snapshot.recorded_at,
                ),
            )

            if self.dual_write:
                # Legacy bitaxe_pool_stats shape
                cursor.execute(
                    """
                    INSERT INTO bitaxe_pool_stats (
                        pool_address, recorded_at,
                        hashrate_1m, hashrate_5m, hashrate_1hr, hashrate_1d, hashrate_7d,
                        lastshare, workers, shares, bestshare, bestever, authorised,
                        hashrate_1m_ghs, hashrate_1d_ghs
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        snapshot.pool_address,
                        snapshot.recorded_at,
                        snapshot.hashrate_1m_display or '0',
                        snapshot.hashrate_5m_display or '0',
                        snapshot.hashrate_1h_display or '0',
                        snapshot.hashrate_1d_display or '0',
                        snapshot.hashrate_7d_display or '0',
                        snapshot.last_share_unix or 0,
                        snapshot.workers or 0,
                        snapshot.shares or 0,
                        snapshot.best_share or 0.0,
                        int(snapshot.best_ever or 0),
                        snapshot.authorised_unix or snapshot.pool_total_miners or 0,
                        snapshot.hashrate_1m_ghs or 0.0,
                        snapshot.hashrate_1d_ghs or snapshot.hashrate_1m_ghs or 0.0,
                    ),
                )

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to write pool snapshot: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            conn.close()
