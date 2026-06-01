#!/usr/bin/env python3
"""
Test the complete Avalon data collection without database
"""

import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

# Portable path setup: add data-service root so "from collectors..." and "from notifications..." work
# regardless of cwd, invocation dir, or CI environment. Fixes previous hardcoded /Users/... path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def socket_request(ip, command, timeout=10):
    """Make TCP socket request to Avalon device using cgminer API."""
    sock = None
    try:
        # Create socket connection to cgminer API (port 4028)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, 4028))

        # Send command
        sock.send(command.encode('utf-8'))

        # Receive response
        response = b''
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                response += data
            except socket.timeout:
                break

        response_str = response.decode('utf-8', errors='ignore').strip()

        # Debug: print raw response for estates command
        if command == 'estats':
            print(f"   Raw estats response length: {len(response_str)}")
            print(f"   Raw response contains OTemp: {'OTemp' in response_str}")

        return parse_cgminer_response(response_str)

    except Exception as e:
        print(f"Socket request failed for {ip}: {e}")
        raise
    finally:
        if sock:
            sock.close()

def parse_cgminer_response(response_str):
    """Parse cgminer API response format."""
    try:
        # cgminer responses are in format: STATUS=...|DATA=...|
        parts = response_str.split('|')
        parsed_data = {}

        for part in parts:
            if '=' in part and ',' in part:
                # Parse key=value pairs separated by commas
                pairs = part.split(',')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        parsed_data[key.strip()] = value.strip()
            elif '=' in part:
                # Single key=value pair
                key, value = part.split('=', 1)
                parsed_data[key.strip()] = value.strip()

        return parsed_data

    except Exception as e:
        print(f"Error parsing cgminer response: {e}")
        return {}

def parse_hashrate_mhs(mhs_str):
    """Parse MHS (Megahashes per second) to GH/s."""
    try:
        mhs_value = float(mhs_str)
        return mhs_value / 1000.0  # Convert MH/s to GH/s
    except (ValueError, TypeError):
        return 0.0

def parse_temperature_from_stats(stats_info):
    """Parse temperature from estats response."""
    try:
        mm_id0 = stats_info.get('MM ID0', '')

        # Look for OTemp[value] pattern
        otemp_match = re.search(r'OTemp\[(\d+)\]', mm_id0)
        if otemp_match and otemp_match.group(1) != '-273':
            return float(otemp_match.group(1))

        # Fallback to TAvg[value]
        tavg_match = re.search(r'TAvg\[(\d+)\]', mm_id0)
        if tavg_match:
            return float(tavg_match.group(1))

        return 0.0
    except (ValueError, TypeError):
        return 0.0

def test_complete_data_collection():
    """Test complete data collection from the Avalon device.
    Skipped automatically when device is unreachable.
    """
    import pytest
    device_ip = "192.168.1.100"

    # Skip test if device is not reachable (no live hardware in CI)
    try:
        import socket as _socket
        s = _socket.create_connection((device_ip, 4028), timeout=2)
        s.close()
    except OSError:
        pytest.skip(f"Avalon device not reachable at {device_ip}:4028 — skipping live test")

    version_info = socket_request(device_ip, 'version')
    assert version_info, "version command returned empty response"

    summary_info = socket_request(device_ip, 'summary')
    hashrate_ghs = parse_hashrate_mhs(summary_info.get('MHS av', '0'))
    assert hashrate_ghs > 0, "Hashrate should be positive on a live device"

    uptime_seconds = int(summary_info.get('Elapsed', 0))
    shares_accepted = int(summary_info.get('Accepted', 0))
    shares_rejected = int(summary_info.get('Rejected', 0))
    assert uptime_seconds >= 0
    assert shares_accepted >= 0

    stats_info = socket_request(device_ip, 'estats')
    temperature_c = parse_temperature_from_stats(stats_info)
    assert temperature_c > 0, "Temperature should be positive on a live device"

    pools_info = socket_request(device_ip, 'pools')
    assert pools_info is not None, "Pools command should return data"

if __name__ == "__main__":
    test_complete_data_collection()