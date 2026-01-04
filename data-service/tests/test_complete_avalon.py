#!/usr/bin/env python3
"""
Test the complete Avalon collector end-to-end with live device
"""

import os
import sys

sys.path.append('/Users/davidebert/Desktop/Documents/MinerSentinel/data-service')

# Mock the database environment to avoid connection issues
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

def test_complete_collector():
    """Test the complete collector with live device but without database."""

    # Import after setting environment
    from collectors.avalon_collector import AvalonCollector

    device_ip = "192.168.1.100"  # Replace with your Avalon device IP
    device_ids = [device_ip]
    database_url = 'postgresql://test:test@localhost:5432/test'

    print(f"Testing complete Avalon collector with device {device_ip}")
    print("=" * 60)

    try:
        # Create collector instance
        collector = AvalonCollector(device_ids, database_url)

        # Test device data collection (this should work without database)
        print("1. Testing device data collection...")

        # Test socket request
        version_info = collector._socket_request(device_ip, 'version')
        print(f"   Device: {version_info.get('PROD', 'Unknown')} v{version_info.get('CGMiner', 'Unknown')}")

        # Test summary
        summary_info = collector._socket_request(device_ip, 'summary')
        hashrate = collector._parse_hashrate_mhs(summary_info.get('MHS av', '0'))
        print(f"   Hashrate: {hashrate:.2f} GH/s")

        # Test estats with all parsing functions
        print("\n2. Testing hardware stats parsing...")
        stats_info = collector._socket_request(device_ip, 'estats')

        temperature = collector._parse_temperature_from_stats(stats_info)
        power = collector._parse_power_from_stats(stats_info)
        fan_speed = collector._parse_fan_speed_from_stats(stats_info)
        frequency = collector._parse_frequency_from_stats(stats_info)
        voltage = collector._parse_voltage_from_stats(stats_info)
        memory_usage = collector._parse_memory_usage_from_stats(stats_info)

        print(f"   Temperature: {temperature}°C")
        print(f"   Power: {power:.1f} W")
        print(f"   Fan Speed: {fan_speed} RPM")
        print(f"   Frequency: {frequency:.2f} MHz")
        print(f"   Voltage: {voltage:.2f} V")
        print(f"   Memory Usage: {memory_usage:.1f}%")

        # Test efficiency calculation
        if hashrate > 0 and power > 0:
            efficiency = power / hashrate  # J/GH
            print(f"   Efficiency: {efficiency:.2f} J/GH")

        # Test pools
        print("\n3. Testing pool information...")
        pools_info = collector._socket_request(device_ip, 'pools')
        pool_url = pools_info.get('URL', 'Unknown')
        pool_user = pools_info.get('User', 'Unknown')
        accepted = pools_info.get('Accepted', 0)
        rejected = pools_info.get('Rejected', 0)

        print(f"   Pool URL: {pool_url}")
        print(f"   Pool User: {pool_user}")
        print(f"   Shares - Accepted: {accepted}, Rejected: {rejected}")

        print("\n✅ Complete collector test successful!")
        print("\nCollected data summary:")
        print(f"- Device: Avalon Nano3s running CGMiner {version_info.get('CGMiner', 'Unknown')}")
        print(f"- Hashrate: {hashrate:.2f} GH/s at {frequency:.1f} MHz")
        print(f"- Temperature: {temperature}°C, Fan: {fan_speed} RPM")
        print(f"- Power: {power:.1f}W ({efficiency:.2f} J/GH)")
        print(f"- Voltage: {voltage:.2f}V, Memory: {memory_usage:.1f}%")
        print(f"- Pool: {pool_url.replace('stratum+tcp://', '')}")

        return True

    except Exception as e:
        print(f"\n❌ Collector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_complete_collector()