#!/usr/bin/env python3
"""
Test Bitaxe collector with Nerdqaxe device response (missing overheat_mode)
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path to import collectors
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBitaxeNerdqaxeSupport(unittest.TestCase):
    """Test that Bitaxe collector handles Nerdqaxe devices correctly."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock database URL
        self.database_url = 'postgresql://test:test@localhost:5432/test'
        
    @patch('psycopg2.connect')
    @patch('requests.get')
    def test_nerdqaxe_missing_overheat_mode(self, mock_get, mock_connect):
        """Test that collector handles Nerdqaxe response without overheat_mode field."""
        from collectors.bitaxe_collector import BitAxeCollector
        
        # Mock Nerdqaxe API response (missing overheat_mode, rotation, displayTimeout)
        nerdqaxe_response = {
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
            'isPSRAMAvailable': 1
        }
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = nerdqaxe_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, 'Test Nerdqaxe')  # device_db_id, device_name
        mock_cursor.fetchall.return_value = []  # No previous hashrates
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create collector and test
        collector = BitAxeCollector(self.database_url)
        
        # This should NOT raise a psycopg2.errors.NotNullViolation error
        try:
            collector.collect_device_data('test-device', '192.168.1.100')
            
            # Verify the cursor was called with the expected parameters
            self.assertTrue(mock_cursor.execute.called)
            
            # Get the last execute call for the system_info INSERT
            calls = [call for call in mock_cursor.execute.call_args_list 
                    if 'bitaxe_system_info' in str(call)]
            
            self.assertTrue(len(calls) > 0, "Expected INSERT into bitaxe_system_info")
            
            # Extract the parameters from the INSERT call
            insert_call = calls[0]
            params = insert_call[0][1]  # Second argument to execute() is the parameters tuple
            
            # Find the overheat_mode parameter (it's at index 20 based on the INSERT statement)
            # Parameters: device_id(0), recorded_at(1), ASICModel(2), boardVersion(3), hostname(4), 
            # macAddr(5), version(6), axeOSVersion(7), idfVersion(8), runningPartition(9),
            # ssid(10), wifiStatus(11), wifiRSSI(12), coreVoltage(13), coreVoltageActual(14),
            # expectedHashrate(15), poolDifficulty(16), smallCoreCount(17),
            # vrTemp(18), temptarget(19), overheat_mode(20), ...
            overheat_mode_value = params[20]
            
            # Verify overheat_mode has a default value of 0 instead of None
            self.assertEqual(overheat_mode_value, 0, 
                           f"Expected overheat_mode to be 0 (default), got {overheat_mode_value}")
            
            # Also verify rotation (at index 28) and displayTimeout (at index 30)
            # auto_fan_speed(21), fan_speed_percent(22), min_fan_speed(23),
            # max_power(24), nominal_voltage(25), overclock_enabled(26),
            # display_type(27), display_rotation(28), invert_screen(29), display_timeout(30)
            rotation_value = params[28]
            display_timeout_value = params[30]
            
            self.assertEqual(rotation_value, 0, 
                           f"Expected rotation to be 0 (default), got {rotation_value}")
            self.assertEqual(display_timeout_value, -1, 
                           f"Expected displayTimeout to be -1 (default), got {display_timeout_value}")
            
            print("✅ Test passed: Nerdqaxe device with missing fields handled correctly")
            
        except Exception as e:
            self.fail(f"Collector raised an exception with Nerdqaxe response: {e}")
    
    @patch('psycopg2.connect')
    @patch('requests.get')
    def test_standard_bitaxe_with_all_fields(self, mock_get, mock_connect):
        """Test that collector still works with standard Bitaxe response including all fields."""
        from collectors.bitaxe_collector import BitAxeCollector
        
        # Mock standard Bitaxe API response (with all fields)
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
            'overheat_mode': 0,  # Present in standard Bitaxe
            'autofanspeed': 1,
            'fanspeed': 75,
            'minFanSpeed': 30,
            'maxPower': 25.0,
            'nominalVoltage': 5.0,
            'overclockEnabled': 0,
            'display': 'OLED',
            'rotation': 0,  # Present in standard Bitaxe
            'invertscreen': 0,
            'displayTimeout': 60,  # Present in standard Bitaxe
            'stratumPort': 3333,
            'fallbackStratumURL': '',
            'fallbackStratumPort': None,
            'isUsingFallbackStratum': 0,
            'freeHeap': 100000,
            'isPSRAMAvailable': 1
        }
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = standard_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (2, 'Test Bitaxe')
        mock_cursor.fetchall.return_value = []
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create collector and test
        collector = BitAxeCollector(self.database_url)
        
        try:
            collector.collect_device_data('test-device', '192.168.1.101')
            
            # Verify it still works with all fields present
            self.assertTrue(mock_cursor.execute.called)
            print("✅ Test passed: Standard Bitaxe device with all fields handled correctly")
            
        except Exception as e:
            self.fail(f"Collector raised an exception with standard Bitaxe response: {e}")


if __name__ == '__main__':
    unittest.main()
