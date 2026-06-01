#!/usr/bin/env python3
"""
Test the Avalon collector directly without Docker to validate the fix
"""

import logging
import os
import sys
from pathlib import Path

# Portable path setup at module load (used by inner test code too)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mock the database environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

def test_collector_socket_communication():
    """Test the collector's socket communication directly."""

    # (path already set portably at top of file)

    # Import the collector class without database dependencies
    import json
    import re
    import socket
    from datetime import datetime, timezone

    class TestAvalonCollector:
        """Test version of collector with just socket communication."""

        def _socket_request(self, ip, command, timeout=10):
            """Make TCP socket request to Avalon device using cgminer API."""
            sock = None
            try:
                # Create socket connection to cgminer API (port 4028)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((ip, 4028))

                # Send command in JSON format as required by cgminer API
                command_json = json.dumps({"command": command})
                sock.send(command_json.encode('utf-8'))

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
                print(f"Socket response from {ip}: {response_str[:200]}...")

                # Parse JSON response directly
                response_str = response_str.replace('\x00', '')

                try:
                    parsed = json.loads(response_str)
                    # Return the actual data part based on command
                    if isinstance(parsed, dict):
                        if command.upper() in parsed and parsed[command.upper()]:
                            return parsed[command.upper()][0] if isinstance(parsed[command.upper()], list) else parsed[command.upper()]
                        elif command.lower() == 'version' and 'VERSION' in parsed and parsed['VERSION']:
                            return parsed['VERSION'][0]
                        elif command.lower() == 'summary' and 'SUMMARY' in parsed and parsed['SUMMARY']:
                            return parsed['SUMMARY'][0]
                        elif command.lower() == 'estats' and 'STATS' in parsed and parsed['STATS']:
                            return parsed['STATS'][0]
                        elif command.lower() == 'pools' and 'POOLS' in parsed and parsed['POOLS']:
                            return parsed['POOLS'][0]  # Return first pool
                        else:
                            # Return full response for debugging
                            return parsed
                    return parsed
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON response from {ip}: {response_str[:500]}")
                    return {"raw_response": response_str}

            except Exception as e:
                print(f"Socket request failed for {ip}: {e}")
                raise
            finally:
                if sock:
                    sock.close()

        def _parse_hashrate_mhs(self, mhs_str):
            """Parse MHS (Megahashes per second) to GH/s."""
            try:
                mhs_value = float(mhs_str)
                return mhs_value / 1000.0  # Convert MH/s to GH/s
            except (ValueError, TypeError):
                return 0.0

        def _parse_power_from_stats(self, stats_info):
            """Parse power consumption from estats response."""
            try:
                mm_id0 = stats_info.get('MM ID0', '')

                # Try PS array (last value is power in watts)
                ps_match = re.search(r'PS\[([^\]]+)\]', mm_id0)
                if ps_match:
                    ps_values = ps_match.group(1).split()
                    if len(ps_values) >= 7:
                        power_watts = float(ps_values[6])
                        return power_watts

                # Fallback: Try MPO field
                mpo_match = re.search(r'MPO\[(\d+)\]', mm_id0)
                if mpo_match:
                    return float(mpo_match.group(1))

                return 0.0
            except (ValueError, TypeError, IndexError):
                return 0.0

        def _parse_temperature_from_stats(self, stats_info):
            """Parse temperature from estats response."""
            try:
                mm_id0 = stats_info.get('MM ID0', '')
                otemp_match = re.search(r'OTemp\[(\d+)\]', mm_id0)
                if otemp_match and otemp_match.group(1) != '-273':
                    return float(otemp_match.group(1))
                return 0.0
            except (ValueError, TypeError):
                return 0.0

    # Test the collector
    collector = TestAvalonCollector()
    device_ip = "192.168.1.100"

    # Skip if device is unreachable (no live hardware in CI)
    import socket as _socket
    try:
        s = _socket.create_connection((device_ip, 4028), timeout=2)
        s.close()
    except OSError:
        import pytest
        pytest.skip(f"Avalon device not reachable at {device_ip}:4028 — skipping live test")

    version_info = collector._socket_request(device_ip, 'version')
    assert version_info, "version command returned empty response"

    summary_info = collector._socket_request(device_ip, 'summary')
    mhs_av = summary_info.get('MHS av', 0)
    hashrate_ghs = collector._parse_hashrate_mhs(mhs_av)
    assert hashrate_ghs > 0, f"Hashrate should be positive, got {hashrate_ghs}"

    stats_info = collector._socket_request(device_ip, 'estats')
    temperature = collector._parse_temperature_from_stats(stats_info)
    power = collector._parse_power_from_stats(stats_info)

    assert temperature > 0, f"Temperature should be positive, got {temperature}"
    assert power > 0, f"Power should be positive, got {power}"

if __name__ == "__main__":
    test_collector_socket_communication()
    print("Collector test complete.")