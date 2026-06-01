#!/usr/bin/env python3
"""
Test the complete Avalon collector end-to-end with live device.
Marked as integration — skipped automatically when device is unreachable.
"""

import os
import socket
import sys
from pathlib import Path

import pytest

# Portable path setup: add data-service root so "from collectors..." and "from notifications..." work
# regardless of cwd, invocation dir, or CI environment. Fixes previous hardcoded /Users/... path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock the database environment to avoid connection issues
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

DEVICE_IP = "192.168.1.100"


def _device_reachable(ip, port=4028, timeout=2):
    try:
        s = socket.create_connection((ip, port), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False


@pytest.mark.integration
def test_complete_collector():
    """Test the complete collector with live device but without database."""

    # Import after setting environment
    from collectors.avalon_collector import AvalonCollector

    if not _device_reachable(DEVICE_IP):
        pytest.skip(f"Avalon device not reachable at {DEVICE_IP}:4028 — skipping live test")

    database_url = 'postgresql://test:test@localhost:5432/test'
    collector = AvalonCollector(database_url)

    version_info = collector._socket_request(DEVICE_IP, 'version')
    assert version_info, "version command returned empty response"

    summary_info = collector._socket_request(DEVICE_IP, 'summary')
    hashrate = collector._parse_hashrate_mhs(summary_info.get('MHS av', '0'))
    assert hashrate > 0, "Hashrate should be positive on a live device"

    stats_info = collector._socket_request(DEVICE_IP, 'estats')
    temperature = collector._parse_temperature_from_stats(stats_info)
    power = collector._parse_power_from_stats(stats_info)
    fan_speed = collector._parse_fan_speed_from_stats(stats_info)
    frequency = collector._parse_frequency_from_stats(stats_info)
    voltage = collector._parse_voltage_from_stats(stats_info)
    memory_usage = collector._parse_memory_usage_from_stats(stats_info)

    assert temperature > 0, "Temperature should be positive"
    assert power > 0, "Power should be positive"
    assert fan_speed >= 0, "Fan speed should be non-negative"
    assert frequency > 0, "Frequency should be positive"
    assert voltage >= 0, "Voltage should be non-negative"
    assert 0 <= memory_usage <= 100, "Memory usage should be 0-100%"

    pools_info = collector._socket_request(DEVICE_IP, 'pools')
    assert pools_info is not None, "Pools command should return data"

if __name__ == "__main__":
    test_complete_collector()