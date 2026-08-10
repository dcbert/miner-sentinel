"""
Normalized snapshots and unified-table persistence for multi-make miners and pools.

Adapters fill these dataclasses in canonical units; writers own SQL (Release C).
"""
from __future__ import annotations

import logging
import re
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


def parse_difficulty(value: Any) -> float:
    """
    Parse difficulty from int/float or strings like '22.3 M', '20.64G', '1.036K'.
    """
    if value is None or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    match = re.match(r'([\d.]+)\s*([KMGT])?', str(value).strip(), re.IGNORECASE)
    if not match:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    num = float(match.group(1))
    unit = (match.group(2) or '').upper()
    multipliers = {'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}
    return num * multipliers.get(unit, 1.0)


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
    """Persist normalized device snapshots to unified tables (Release C: unified only)."""

    def __init__(self, database_url: str, dual_write: bool = False):
        """dual_write is accepted for API compatibility but ignored (always False)."""
        self.database_url = database_url
        self.dual_write = False

    def get_connection(self):
        return psycopg2.connect(self.database_url)

    def resolve_device_db_id(self, cursor, make: str, device_id: str) -> Optional[int]:
        cursor.execute(
            "SELECT id FROM devices WHERE make = %s AND device_id = %s",
            (make, device_id),
        )
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

            # Update last_seen on unified registry
            cursor.execute(
                """
                UPDATE devices
                SET last_seen_at = NOW(), error_message = NULL
                WHERE id = %s
                """,
                (device_db_id,),
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

class PoolDataWriter:
    """Persist normalized pool snapshots to pool_stats only (Release C)."""

    def __init__(self, database_url: str = None, dual_write: bool = False, connection=None):
        """
        Prefer an existing ``connection`` (shared collector conn).
        ``database_url`` is only used when no connection is provided.

        Note: psycopg2 ``connection.dsn`` omits the password, so never rebuild
        a URL from dsn alone — that causes auth failures on a second connect.
        """
        self.database_url = database_url
        self.dual_write = False  # Release C: unified only
        self.connection = connection

    def get_connection(self):
        if self.connection is not None:
            # Reconnect if the shared connection was closed mid-cycle
            if getattr(self.connection, 'closed', 0):
                if not self.database_url:
                    raise RuntimeError('Pool DB connection is closed and no database_url is set')
                return psycopg2.connect(self.database_url), True
            return self.connection, False
        if not self.database_url:
            raise RuntimeError('PoolDataWriter requires connection or database_url')
        return psycopg2.connect(self.database_url), True

    def write_snapshot(self, snapshot: NormalizedPoolSnapshot) -> None:
        conn, owns = self.get_connection()
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

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to write pool snapshot: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
            if owns:
                conn.close()