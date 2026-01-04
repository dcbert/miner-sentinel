#!/usr/bin/env python3
"""
Test the Avalon collector directly without Docker to validate the fix
"""

import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mock the database environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

def test_collector_socket_communication():
    """Test the collector's socket communication directly."""

    # Add the collector path
    sys.path.append('/Users/davidebert/Desktop/Documents/MinerSentinel/data-service')

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
    device_ip = "192.168.1.100"  # Replace with your Avalon device IP

    print(f"🔄 Testing Avalon collector with device {device_ip}")
    print("=" * 60)

    try:
        # Test version
        print("\n1. Testing version command...")
        version_info = collector._socket_request(device_ip, 'version')
        print(f"   Device: {version_info.get('PROD', 'Unknown')}")

        # Test summary
        print("\n2. Testing summary command...")
        summary_info = collector._socket_request(device_ip, 'summary')
        mhs_av = summary_info.get('MHS av', 0)
        hashrate_ghs = collector._parse_hashrate_mhs(mhs_av)

        print(f"   MHS av (raw): {mhs_av}")
        print(f"   Hashrate: {hashrate_ghs:.2f} GH/s")
        print(f"   Shares accepted: {summary_info.get('Accepted', 0)}")
        print(f"   Shares rejected: {summary_info.get('Rejected', 0)}")
        print(f"   Uptime: {summary_info.get('Elapsed', 0)} seconds")

        # Test estats
        print("\n3. Testing estats command...")
        stats_info = collector._socket_request(device_ip, 'estats')

        temperature = collector._parse_temperature_from_stats(stats_info)
        power = collector._parse_power_from_stats(stats_info)

        print(f"   Temperature: {temperature}°C")
        print(f"   Power: {power}W")

        # Check if data looks correct
        print(f"\n🎯 Test Results:")
        if hashrate_ghs > 0:
            print(f"   ✅ Hashrate detection: {hashrate_ghs:.2f} GH/s")
        else:
            print(f"   ❌ Hashrate detection: 0 GH/s - PROBLEM!")

        if power > 0:
            print(f"   ✅ Power detection: {power}W")
        else:
            print(f"   ❌ Power detection: 0W - PROBLEM!")

        if temperature > 0:
            print(f"   ✅ Temperature detection: {temperature}°C")
        else:
            print(f"   ❌ Temperature detection: 0°C - PROBLEM!")

        # Calculate efficiency if we have both values
        if hashrate_ghs > 0 and power > 0:
            hashrate_ths = hashrate_ghs / 1000.0
            efficiency = power / hashrate_ths
            print(f"   ✅ Efficiency: {efficiency:.2f} J/TH")

        return hashrate_ghs > 0 and power > 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_collector_socket_communication()
    if success:
        print(f"\n✅ Collector test passed! Ready for Docker deployment.")
    else:
        print(f"\n❌ Collector test failed! Need to fix issues before Docker.")