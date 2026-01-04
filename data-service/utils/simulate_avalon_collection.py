#!/usr/bin/env python3
"""
Test Avalon collector functionality by simulating the complete data collection process
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

        # Parse JSON response directly
        response_str = response.decode('utf-8').strip().replace('\x00', '')

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

def parse_hashrate_mhs(mhs_value):
    """Convert MH/s to GH/s."""
    try:
        mhs = float(mhs_value) if mhs_value else 0
        return mhs / 1000.0  # Convert MH/s to GH/s
    except (ValueError, TypeError):
        return 0.0

def parse_temperature_from_stats(stats_info):
    """Parse temperature from estats response."""
    try:
        # Temperature data is in the MM ID0 field
        mm_id0 = stats_info.get('MM ID0', '')

        # Look for OTemp[value] pattern
        otemp_match = re.search(r'OTemp\[(\d+)\]', mm_id0)
        if otemp_match and otemp_match.group(1) != '-273':  # -273 indicates sensor not available
            return float(otemp_match.group(1))

        # Fallback to TAvg[value]
        tavg_match = re.search(r'TAvg\[(\d+)\]', mm_id0)
        if tavg_match:
            return float(tavg_match.group(1))

        return 0.0
    except (ValueError, TypeError):
        return 0.0

def parse_power_from_stats(stats_info):
    """Parse power consumption from estats response."""
    try:
        # Power information is in MM ID0 field: PS[0 0 27541 4 0 3756 133]
        # The actual power in watts is the LAST value in the PS array
        mm_id0 = stats_info.get('MM ID0', '')

        # Try PS array (last value is power in watts)
        ps_match = re.search(r'PS\[([^\]]+)\]', mm_id0)
        if ps_match:
            ps_values = ps_match.group(1).split()
            if len(ps_values) >= 7:
                # Power is the last value (index 6) in watts
                power_watts = float(ps_values[6])
                return power_watts

        # Fallback: Try MPO field
        mpo_match = re.search(r'MPO\[(\d+)\]', mm_id0)
        if mpo_match:
            return float(mpo_match.group(1))

        # Fallback: Try ATA2 array first value
        ata2_match = re.search(r'ATA2\[([^\]]+)\]', mm_id0)
        if ata2_match:
            ata2_values = ata2_match.group(1).split('-')
            if len(ata2_values) >= 1:
                return float(ata2_values[0])

        return 0.0
    except (ValueError, TypeError, IndexError):
        return 0.0

def parse_fan_speed_from_stats(stats_info):
    """Parse fan speed from estats response."""
    try:
        # Fan speed is in MM ID0 field: Fan1[1520]
        mm_id0 = stats_info.get('MM ID0', '')
        fan_match = re.search(r'Fan1\[(\d+)\]', mm_id0)

        if fan_match:
            return int(fan_match.group(1))
        return 0
    except (ValueError, TypeError):
        return 0

def parse_frequency_from_stats(stats_info):
    """Parse frequency from estats response."""
    try:
        # Frequency is in MM ID0 field: Freq[464.89]
        mm_id0 = stats_info.get('MM ID0', '')
        freq_match = re.search(r'Freq\[([\d.]+)\]', mm_id0)

        if freq_match:
            return float(freq_match.group(1))
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def parse_voltage_from_stats(stats_info):
    """Parse voltage from estats response."""
    try:
        # Voltage information is in PVT_V0 field: PVT_V0[299 303 301 303 300 301 306 301 297 296 303 305]
        mm_id0 = stats_info.get('MM ID0', '')
        pvt_v0_match = re.search(r'PVT_V0\[([^\]]+)\]', mm_id0)

        if pvt_v0_match:
            # Get first voltage value and convert from centivolts to volts
            voltage_values = pvt_v0_match.group(1).split()
            if voltage_values:
                voltage_cv = float(voltage_values[0])
                return voltage_cv / 100.0  # Convert centivolts to volts
        return 0.0
    except (ValueError, TypeError, IndexError):
        return 0.0

def parse_memory_usage_from_stats(stats_info):
    """Parse memory usage from estats response."""
    try:
        # Memory free is in MM ID0 field: MEMFREE[63728]
        mm_id0 = stats_info.get('MM ID0', '')
        memfree_match = re.search(r'MEMFREE\[(\d+)\]', mm_id0)

        if memfree_match:
            free_kb = float(memfree_match.group(1))
            estimated_total = 128 * 1024  # Assume 128MB total memory
            used_kb = estimated_total - free_kb
            return max(0, (used_kb / estimated_total) * 100.0)
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def simulate_data_collection():
    """Simulate the complete data collection process."""
    device_ip = "192.168.1.100"  # Replace with your Avalon device IP

    print(f"🔄 Simulating Avalon Nano 3s data collection from {device_ip}")
    print("=" * 70)

    try:
        # Step 1: Device version/identification
        print("📋 Step 1: Device identification...")
        version_info = socket_request(device_ip, 'version')
        device_name = version_info.get('PROD', 'Unknown')
        cgminer_version = version_info.get('CGMiner', 'Unknown')
        model = version_info.get('MODEL', 'Unknown')
        mac_address = version_info.get('MAC', 'Unknown')

        print(f"   ✅ Device: {device_name} {model}")
        print(f"   ✅ CGMiner: v{cgminer_version}")
        print(f"   ✅ MAC: {mac_address}")

        # Step 2: Mining performance
        print("\n⚡ Step 2: Mining performance...")
        summary_info = socket_request(device_ip, 'summary')
        hashrate = parse_hashrate_mhs(summary_info.get('MHS av', '0'))
        accepted = summary_info.get('Accepted', 0)
        rejected = summary_info.get('Rejected', 0)
        hw_errors = summary_info.get('Hardware Errors', 0)
        uptime = summary_info.get('Elapsed', 0)

        print(f"   ✅ Hashrate: {hashrate:.2f} GH/s")
        print(f"   ✅ Uptime: {uptime} seconds ({uptime/3600:.1f} hours)")
        print(f"   ✅ Shares: {accepted} accepted, {rejected} rejected")
        print(f"   ✅ Hardware errors: {hw_errors}")

        # Step 3: Hardware statistics
        print("\n🌡️  Step 3: Hardware statistics...")
        stats_info = socket_request(device_ip, 'estats')

        temperature = parse_temperature_from_stats(stats_info)
        power = parse_power_from_stats(stats_info)
        fan_speed = parse_fan_speed_from_stats(stats_info)
        frequency = parse_frequency_from_stats(stats_info)
        voltage = parse_voltage_from_stats(stats_info)
        memory_usage = parse_memory_usage_from_stats(stats_info)

        print(f"   ✅ Temperature: {temperature}°C")
        print(f"   ✅ Power: {power:.1f} W")
        print(f"   ✅ Fan Speed: {fan_speed} RPM")
        print(f"   ✅ Frequency: {frequency:.1f} MHz")
        print(f"   ✅ Voltage: {voltage:.2f} V")
        print(f"   ✅ Memory Usage: {memory_usage:.1f}%")

        # Step 4: Pool information
        print("\n🌊 Step 4: Pool information...")
        pools_info = socket_request(device_ip, 'pools')
        pool_url = pools_info.get('URL', 'Unknown')
        pool_user = pools_info.get('User', 'Unknown')
        pool_status = pools_info.get('Status', 'Unknown')
        stratum_active = pools_info.get('Stratum Active', False)
        difficulty = pools_info.get('Difficulty Accepted', 0)

        print(f"   ✅ Pool: {pool_url}")
        print(f"   ✅ User: {pool_user}")
        print(f"   ✅ Status: {pool_status}")
        print(f"   ✅ Stratum: {'Active' if stratum_active else 'Inactive'}")
        print(f"   ✅ Difficulty: {difficulty:,.0f}")

        # Step 5: Calculated metrics
        print("\n📊 Step 5: Calculated metrics...")
        efficiency = (power / hashrate) if hashrate > 0 and power > 0 else 0
        reject_rate = (rejected / (accepted + rejected) * 100) if (accepted + rejected) > 0 else 0

        print(f"   ✅ Efficiency: {efficiency:.2f} J/GH")
        print(f"   ✅ Reject Rate: {reject_rate:.2f}%")

        # Summary
        print("\n🎯 Collection Summary:")
        print("=" * 50)
        print(f"Device: {device_name} {model} (v{cgminer_version})")
        print(f"Performance: {hashrate:.1f} GH/s @ {frequency:.0f} MHz")
        print(f"Power: {power:.1f}W ({efficiency:.2f} J/GH)")
        print(f"Temperature: {temperature}°C, Fan: {fan_speed} RPM")
        print(f"Pool: {pool_url.replace('stratum+tcp://', '').split(':')[0]}")
        print(f"Status: {pool_status}, Uptime: {uptime/3600:.1f}h")

        print("\n✅ Data collection simulation completed successfully!")
        print("\n💾 Ready for database storage:")
        print("   - Device registration data")
        print("   - Mining statistics")
        print("   - Hardware logs")
        print("   - System information")

        return True

    except Exception as e:
        print(f"\n❌ Data collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    simulate_data_collection()