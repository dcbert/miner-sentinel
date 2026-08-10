#!/usr/bin/env python3
"""
Test Bitaxe collector with Nerdqaxe device response (missing overheat_mode).

Release B writes unified tables only (dual_write=False). Nerdqaxe-specific
defaults (overheat_mode, rotation, displayTimeout) live in normalize_system_info
details, not legacy bitaxe_system_info inserts.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path to import collectors
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBitaxeNerdqaxeSupport(unittest.TestCase):
    """Test that Bitaxe collector handles Nerdqaxe devices correctly."""

    def setUp(self):
        self.database_url = 'postgresql://test:test@localhost:5432/test'

    def _nerdqaxe_response(self):
        """Nerdqaxe API payload missing overheat_mode, rotation, displayTimeout."""
        return {
            'hashRate': 500.0,
            'sharesAccepted': 100,
            'sharesRejected': 1,
            'uptimeSeconds': 3600,
            'bestDiff': '1.5 M',
            'bestSessionDiff': '500 K',
            'stratumURL': 'stratum+tcp://pool.example.com',
            'stratumUser': 'bc1quser',
            'power': 15.5,
            'temp': 65,
            'fanrpm': 5000,
            'voltage': 1200,
            'frequency': 500,
            'ASICModel': 'BM1368',
            'boardVersion': 'nerdqaxe_v1',
            'hostname': 'nerdqaxe-001',
            'macAddr': '00:11:22:33:44:55',
            'version': '2.1.5',
            'axeOSVersion': 'nerdqaxe-2.1.5',
            'idfVersion': 'v5.1',
            'runningPartition': 'ota_0',
            'ssid': 'TestNetwork',
            'wifiStatus': 'connected',
            'wifiRSSI': -45,
            'coreVoltage': 1200,
            'coreVoltageActual': 1195,
            'expectedHashrate': 550.0,
            'poolDifficulty': 1024,
            'smallCoreCount': 115,
            'vrTemp': 70,
            'temptarget': 75,
            # NOTE: overheat_mode is missing - this is the key test case
            'autofanspeed': 1,
            'fanspeed': 80,
            'minFanSpeed': 20,
            'maxPower': 20.0,
            'nominalVoltage': 5.0,
            'overclockEnabled': 0,
            'display': 'OLED',
            # NOTE: rotation is missing
            'invertscreen': 0,
            # NOTE: displayTimeout is missing
            'stratumPort': 3333,
            'fallbackStratumURL': '',
            'fallbackStratumPort': None,
            'isUsingFallbackStratum': 0,
            'freeHeap': 100000,
            'isPSRAMAvailable': 1,
        }

    def test_nerdqaxe_normalize_defaults_missing_fields(self):
        """Missing Nerdqaxe fields get sensible defaults in normalized snapshot."""
        from collectors.bitaxe_collector import BitAxeCollector

        collector = BitAxeCollector(self.database_url, dual_write=False)
        snap = collector.normalize_system_info(self._nerdqaxe_response(), 'nerdqaxe-1')

        self.assertTrue(snap.online)
        self.assertAlmostEqual(snap.mining.hashrate_ghs, 500.0)
        self.assertAlmostEqual(snap.mining.best_difficulty, 1.5e6)
        self.assertAlmostEqual(snap.mining.best_session_difficulty, 5e5)
        self.assertEqual(snap.system.model_reported, 'BM1368')

        details = snap.system.details
        self.assertEqual(details.get('overheat_mode'), 0)
        self.assertEqual(details.get('display_rotation'), 0)
        self.assertEqual(details.get('display_timeout'), -1)
        self.assertEqual(details.get('board_version'), 'nerdqaxe_v1')

    @patch('psycopg2.connect')
    @patch('requests.get')
    def test_nerdqaxe_collect_writes_unified_tables(self, mock_get, mock_connect):
        """collect_device_data inserts into unified tables, not legacy bitaxe_*."""
        from collectors.bitaxe_collector import BitAxeCollector

        mock_response = Mock()
        mock_response.json.return_value = self._nerdqaxe_response()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Side effects for:
        # - collect_device_data: SELECT id, name FROM devices
        # - write_snapshot: resolve_device_db_id → (1,)
        # - update_device_status: SELECT error_message, last_seen_at, name
        # - check_best_difficulty: previous best row
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (1, 'Test Nerdqaxe'),  # devices registry lookup in collect_device_data
            (1,),  # resolve_device_db_id in write_snapshot
            (None, None, 'Test Nerdqaxe'),  # update_device_status previous state
            None,  # check_best_difficulty previous row
        ]
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        collector = BitAxeCollector(self.database_url, dual_write=False)
        collector.collect_device_data('test-device', '192.168.1.100')

        self.assertTrue(mock_cursor.execute.called)

        sql_blobs = [str(call) for call in mock_cursor.execute.call_args_list]
        unified_mining = [s for s in sql_blobs if 'device_mining_stats' in s]
        unified_system = [s for s in sql_blobs if 'device_system_info' in s]
        legacy_system = [s for s in sql_blobs if 'bitaxe_system_info' in s]

        self.assertTrue(len(unified_mining) > 0, "Expected INSERT into device_mining_stats")
        self.assertTrue(len(unified_system) > 0, "Expected INSERT into device_system_info")
        self.assertEqual(len(legacy_system), 0, "Release B must not write legacy bitaxe_system_info")

    @patch('psycopg2.connect')
    @patch('requests.get')
    def test_standard_bitaxe_with_all_fields(self, mock_get, mock_connect):
        """Collector still works with a full AxeOS payload."""
        from collectors.bitaxe_collector import BitAxeCollector

        standard_response = {
            'hashRate': 600.0,
            'sharesAccepted': 200,
            'sharesRejected': 2,
            'uptimeSeconds': 7200,
            'bestDiff': '2.0 M',
            'bestSessionDiff': '1.0 M',
            'stratumURL': 'stratum+tcp://pool.example.com',
            'stratumUser': 'bc1quser',
            'power': 18.0,
            'temp': 60,
            'fanrpm': 4500,
            'voltage': 1250,
            'frequency': 525,
            'ASICModel': 'BM1368',
            'boardVersion': 'bitaxe_ultra_v1',
            'hostname': 'bitaxe-001',
            'macAddr': '00:AA:BB:CC:DD:EE',
            'version': '2.1.5',
            'axeOSVersion': '2.1.5',
            'idfVersion': 'v5.1',
            'runningPartition': 'ota_0',
            'ssid': 'TestNetwork',
            'wifiStatus': 'connected',
            'wifiRSSI': -50,
            'coreVoltage': 1250,
            'coreVoltageActual': 1245,
            'expectedHashrate': 620.0,
            'poolDifficulty': 2048,
            'smallCoreCount': 115,
            'vrTemp': 68,
            'temptarget': 75,
            'overheat_mode': 0,
            'autofanspeed': 1,
            'fanspeed': 75,
            'minFanSpeed': 30,
            'maxPower': 25.0,
            'nominalVoltage': 5.0,
            'overclockEnabled': 0,
            'display': 'OLED',
            'rotation': 0,
            'invertscreen': 0,
            'displayTimeout': 60,
            'stratumPort': 3333,
            'fallbackStratumURL': '',
            'fallbackStratumPort': None,
            'isUsingFallbackStratum': 0,
            'freeHeap': 100000,
            'isPSRAMAvailable': 1,
        }

        mock_response = Mock()
        mock_response.json.return_value = standard_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (2, 'Test Bitaxe'),
            (2,),
            (None, None, 'Test Bitaxe'),
            None,
        ]
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        collector = BitAxeCollector(self.database_url, dual_write=False)
        collector.collect_device_data('test-device', '192.168.1.101')

        self.assertTrue(mock_cursor.execute.called)
        sql_blobs = [str(call) for call in mock_cursor.execute.call_args_list]
        self.assertTrue(any('device_mining_stats' in s for s in sql_blobs))


if __name__ == '__main__':
    unittest.main()
