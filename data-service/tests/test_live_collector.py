#!/usr/bin/env python3
"""
Test the updated Avalon collector with live device
"""

import sys

sys.path.append('/Users/davidebert/Desktop/Documents/MinerSentinel/data-service')

from collectors.avalon_collector import AvalonCollector


def test_live_collection():
    """Test with live device using the updated collector."""
    device_ip = "192.168.1.100"  # Replace with your Avalon device IP

    # Create collector (without database)
    collector = AvalonCollector([device_ip], 'dummy_url')

    print(f"Testing live Avalon collector with device {device_ip}")
    print("=" * 60)

    try:
        # Test socket request
        print("1. Testing version command...")
        version_info = collector._socket_request(device_ip, 'version')
        print(f"   Device: {version_info.get('PROD', 'Unknown')}")

        print("\n2. Testing summary command...")
        summary_info = collector._socket_request(device_ip, 'summary')
        hashrate = collector._parse_hashrate_mhs(summary_info.get('MHS av', '0'))
        print(f"   Hashrate: {hashrate:.2f} GH/s")

        print("\n3. Testing estats command with updated parsing...")
        stats_info = collector._socket_request(device_ip, 'estats')

        # Check if MM ID0 contains the full hardware data
        mm_id0 = stats_info.get('MM ID0', '')
        print(f"   MM ID0 length: {len(mm_id0)}")
        print(f"   Contains temperature data: {'OTemp' in mm_id0}")

        if len(mm_id0) > 500:  # Should be much longer now
            print(f"   ✅ Full hardware data extracted")

            # Test all parsing functions
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
        else:
            print(f"   ❌ Hardware data still truncated")

        print("\n4. Testing pools command...")
        pools_info = collector._socket_request(device_ip, 'pools')
        pool_url = pools_info.get('URL') if pools_info else None
        pool_user = pools_info.get('User') if pools_info else None
        print(f"   Pool URL: {pool_url}")
        print(f"   Pool User: {pool_user}")

        print("\n✅ Live collector test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Live collector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_live_collection()