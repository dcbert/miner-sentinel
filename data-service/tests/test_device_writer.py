"""Unit tests for DeviceDataWriter (Release C: unified tables only)."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.normalized import (
    DeviceDataWriter,
    HardwareMetrics,
    MiningMetrics,
    NormalizedDeviceSnapshot,
    SystemMetrics,
)


def _online_snapshot(device_id='bx-1', make='bitaxe'):
    now = datetime.now(timezone.utc)
    return NormalizedDeviceSnapshot(
        make=make,
        device_id=device_id,
        online=True,
        recorded_at=now,
        mining=MiningMetrics(
            hashrate_ghs=100.0,
            hashrate_avg_ghs=None,
            shares_accepted=10,
            shares_rejected=1,
            hardware_errors=None,
            blocks_found=0,
            uptime_seconds=3600,
            best_difficulty=1e6,
            best_session_difficulty=1e5,
            pool_url='stratum+tcp://pool',
            pool_user='user',
        ),
        hardware=HardwareMetrics(
            temperature_c=55.0,
            temperature_board_c=None,
            temperature_chip_c=None,
            power_watts=20.0,
            efficiency_j_per_th=40.0,
            fan_speed_rpm=3000,
            fan_speed_percent=80,
            voltage=1.2,
            frequency_mhz=500.0,
        ),
        system=SystemMetrics(
            hostname='axe',
            mac_address='aa:bb',
            firmware_version='v1',
            serial_number=None,
            model_reported='BM1366',
            expected_hashrate_ghs=110.0,
            primary_pool_url='stratum+tcp://pool',
            primary_pool_user='user',
            fallback_pool_url=None,
            fallback_pool_user=None,
            using_fallback_pool=False,
            wifi_ssid='net',
            wifi_rssi=-40,
            details={'overheat_mode': 0},
        ),
    )


@patch('collectors.normalized.psycopg2.connect')
def test_device_writer_inserts_three_series(mock_connect):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (42,)  # resolve_device_db_id
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    writer = DeviceDataWriter('postgresql://u:p@localhost/db')
    result = writer.write_snapshot(_online_snapshot())
    assert result == 42

    sqls = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
    assert 'device_mining_stats' in sqls
    assert 'device_hardware_stats' in sqls
    assert 'device_system_info' in sqls
    assert 'bitaxe_mining_stats' not in sqls
    mock_conn.commit.assert_called()


@patch('collectors.normalized.psycopg2.connect')
def test_device_writer_updates_last_seen(mock_connect):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (7,)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    writer = DeviceDataWriter('postgresql://u:p@localhost/db')
    writer.write_snapshot(_online_snapshot())
    sqls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any('last_seen_at' in s and 'UPDATE devices' in s for s in sqls)


@patch('collectors.normalized.psycopg2.connect')
def test_device_writer_offline_sets_error(mock_connect):
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    snap = NormalizedDeviceSnapshot(
        make='bitaxe',
        device_id='bx-off',
        online=False,
        recorded_at=datetime.now(timezone.utc),
        mining=None,
        hardware=None,
        system=None,
        error_message='timeout',
    )
    writer = DeviceDataWriter('postgresql://u:p@localhost/db')
    assert writer.write_snapshot(snap) is None
    sqls = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
    assert 'UPDATE devices' in sqls
    assert 'error_message' in sqls


@patch('collectors.normalized.psycopg2.connect')
def test_writer_unknown_device_id(mock_connect):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # not in registry
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    writer = DeviceDataWriter('postgresql://u:p@localhost/db')
    assert writer.write_snapshot(_online_snapshot(device_id='missing')) is None
