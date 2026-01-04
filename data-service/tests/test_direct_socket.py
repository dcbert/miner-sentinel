#!/usr/bin/env python3
"""
Test the Avalon socket communication directly without database dependencies
"""

import json
import re
import socket


def socket_request(ip, command, port=4028, timeout=30):
    """Send command to cgminer API via socket."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        # Connect and send command
        sock.connect((ip, port))
        sock.send(json.dumps({"command": command}).encode('utf-8'))

        # Read response (cgminer closes connection after response)
        response = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                break

        sock.close()

        if not response:
            return {}

        # Parse cgminer response format
        response_str = response.decode('utf-8').strip()

        # Remove null bytes
        response_str = response_str.replace('\x00', '')

        # cgminer response is pure JSON
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
            return {"raw_response": response_str}

    except Exception as e:
        return {"error": str(e)}

def parse_temperature_from_stats(stats_info):
    """Extract temperature from MM ID0 field."""
    mm_id0 = stats_info.get('MM ID0', '')
    temp_match = re.search(r'OTemp\[(\d+)\]', mm_id0)
    return float(temp_match.group(1)) if temp_match else 0.0

def parse_power_from_stats(stats_info):
    """Extract power consumption from MM ID0 field."""
    mm_id0 = stats_info.get('MM ID0', '')
    # PS array format: PS[0 0 27543 4 0 3756 133] - power is typically the 6th element (3756)
    ps_match = re.search(r'PS\[([^\]]+)\]', mm_id0)
    if ps_match:
        ps_values = ps_match.group(1).split()
        if len(ps_values) >= 6:
            try:
                return float(ps_values[5]) / 1000.0  # Convert to watts
            except ValueError:
                pass
    return 0.0

def parse_fan_speed_from_stats(stats_info):
    """Extract fan speed from MM ID0 field."""
    mm_id0 = stats_info.get('MM ID0', '')
    fan_match = re.search(r'Fan1\[(\d+)\]', mm_id0)
    return int(fan_match.group(1)) if fan_match else 0

def parse_frequency_from_stats(stats_info):
    """Extract frequency from MM ID0 field."""
    mm_id0 = stats_info.get('MM ID0', '')
    freq_match = re.search(r'Freq\[([\d.]+)\]', mm_id0)
    return float(freq_match.group(1)) if freq_match else 0.0

def parse_voltage_from_stats(stats_info):
    """Extract average voltage from MM ID0 field."""
    mm_id0 = stats_info.get('MM ID0', '')
    # PVT_V0 array format: PVT_V0[299 303 302 303 ...] - take average and convert from mV to V
    volt_match = re.search(r'PVT_V0\[([^\]]+)\]', mm_id0)
    if volt_match:
        volt_values = volt_match.group(1).split()
        try:
            volt_nums = [float(v) for v in volt_values if v.isdigit()]
            if volt_nums:
                avg_voltage = sum(volt_nums) / len(volt_nums)
                return avg_voltage / 100.0  # Convert from mV*10 to V (299 -> 2.99V)
        except ValueError:
            pass
    return 0.0

def parse_memory_usage_from_stats(stats_info):
    """Extract memory usage from MM ID0 field."""
    mm_id0 = stats_info.get('MM ID0', '')
    # MEMFREE shows free memory, calculate usage percentage
    memfree_match = re.search(r'MEMFREE\[(\d+)\]', mm_id0)
    if memfree_match:
        free_mem = int(memfree_match.group(1))
        # Assume total memory is around 128MB for Avalon Nano 3s
        total_mem = 128 * 1024  # 128MB in KB
        used_mem = total_mem - free_mem
        return (used_mem / total_mem) * 100.0
    return 0.0

def parse_hashrate_mhs(mhs_value):
    """Convert MH/s to GH/s."""
    try:
        mhs = float(mhs_value) if mhs_value else 0
        return mhs / 1000.0  # Convert MH/s to GH/s
    except (ValueError, TypeError):
        return 0.0

def test_live_device():
    """Test with live Avalon device - replace IP with your device"""
    device_ip = "192.168.1.100"  # Replace with your Avalon device IP

    print(f"Testing live Avalon device at {device_ip}")
    print("=" * 60)

    try:
        # Test version
        print("1. Testing version command...")
        version_info = socket_request(device_ip, 'version')
        print(f"   Response: {version_info}")

        # Test summary
        print("\n2. Testing summary command...")
        summary_info = socket_request(device_ip, 'summary')
        print(f"   Response keys: {list(summary_info.keys()) if isinstance(summary_info, dict) else 'Not a dict'}")

        if 'MHS av' in summary_info:
            hashrate = parse_hashrate_mhs(summary_info.get('MHS av', '0'))
            print(f"   Hashrate: {hashrate:.2f} GH/s")

        # Test estats with focus on MM ID0
        print("\n3. Testing estats command...")
        stats_info = socket_request(device_ip, 'estats')
        print(f"   Response keys: {list(stats_info.keys()) if isinstance(stats_info, dict) else 'Not a dict'}")

        if 'MM ID0' in stats_info:
            mm_id0 = stats_info['MM ID0']
            print(f"   MM ID0 length: {len(mm_id0)}")
            print(f"   Full MM ID0 content:")
            print(f"   {mm_id0}")

            # Look for temperature-related patterns
            print(f"\n   Searching for temperature patterns:")
            if 'OTemp' in mm_id0:
                print(f"   Found OTemp in MM ID0")
            if 'Temp' in mm_id0:
                print(f"   Found Temp in MM ID0")
            if 'Power' in mm_id0:
                print(f"   Found Power in MM ID0")
            if 'Fan' in mm_id0:
                print(f"   Found Fan in MM ID0")

            # Test parsing functions
            temperature = parse_temperature_from_stats(stats_info)
            power = parse_power_from_stats(stats_info)
            fan_speed = parse_fan_speed_from_stats(stats_info)
            frequency = parse_frequency_from_stats(stats_info)
            voltage = parse_voltage_from_stats(stats_info)
            memory_usage = parse_memory_usage_from_stats(stats_info)

            print(f"\n   Parsed values:")
            print(f"   Temperature: {temperature}°C")
            print(f"   Power: {power:.1f} W")
            print(f"   Fan Speed: {fan_speed} RPM")
            print(f"   Frequency: {frequency:.2f} MHz")
            print(f"   Voltage: {voltage:.2f} V")
            print(f"   Memory Usage: {memory_usage:.1f}%")

        # Test pools
        print("\n4. Testing pools command...")
        pools_info = socket_request(device_ip, 'pools')
        print(f"   Response: {pools_info}")

        print("\n✅ Direct socket test completed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_live_device()