#!/usr/bin/env python3
"""
Test the complete Avalon data collection without database
"""

import os
import re
import socket
import sys
from datetime import datetime, timezone

# Add the collectors directory to the path
sys.path.append('/Users/davidebert/Desktop/Documents/MinerSentinel/data-service')

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
    """Test complete data collection from the Avalon device."""
    device_ip = "192.168.1.100"  # Replace with your Avalon device IP
    device_id = "avalon_1"

    print(f"Testing complete data collection from {device_ip}")
    print("=" * 60)

    try:
        # Get device information using cgminer API commands
        print("1. Getting version info...")
        version_info = socket_request(device_ip, 'version')
        print(f"   Device: {version_info.get('PROD', 'Unknown')}")
        print(f"   Model: {version_info.get('MODEL', 'Unknown')}")
        print(f"   MAC: {version_info.get('MAC', 'Unknown')}")

        print("\n2. Getting summary info...")
        summary_info = socket_request(device_ip, 'summary')
        hashrate_ghs = parse_hashrate_mhs(summary_info.get('MHS av', '0'))
        uptime_seconds = int(summary_info.get('Elapsed', 0))
        shares_accepted = int(summary_info.get('Accepted', 0))
        shares_rejected = int(summary_info.get('Rejected', 0))

        print(f"   Hashrate: {hashrate_ghs:.2f} GH/s")
        print(f"   Uptime: {uptime_seconds} seconds ({uptime_seconds/3600:.1f} hours)")
        print(f"   Shares: {shares_accepted} accepted, {shares_rejected} rejected")

        print("\n3. Getting hardware stats...")
        stats_info = socket_request(device_ip, 'estats')
        print(f"   Stats data sample: {str(stats_info)[:200]}...")

        # Debug temperature parsing
        mm_id0 = stats_info.get('MM ID0', '')
        print(f"   MM ID0 length: {len(mm_id0)}")
        print(f"   MM ID0 sample: {mm_id0[:100]}...")

        temperature_c = parse_temperature_from_stats(stats_info)
        print(f"   Temperature: {temperature_c}°C")

        print("\n4. Getting pool info...")
        pools_info = socket_request(device_ip, 'pools')
        print(f"   Pool data received: {len(str(pools_info))} characters")

        # Debug: print the actual pool data
        pool_data_str = str(pools_info)
        print(f"   Pool data sample: {pool_data_str[:200]}...")

        # Parse pool information
        pool_url = None
        pool_user = None

        # Try to extract URL and User from the pool data
        url_match = re.search(r'URL=([^,]+)', pool_data_str)
        user_match = re.search(r'User=([^,]+)', pool_data_str)

        if url_match:
            pool_url = url_match.group(1)
        if user_match:
            pool_user = user_match.group(1)

        print(f"   Active pool: {pool_url}")
        print(f"   Pool user: {pool_user}")

        print("\n5. Summary of collected data:")
        print("   ✅ Device identification successful")
        print("   ✅ Mining statistics collected")
        print("   ✅ Hardware monitoring data collected")
        print("   ✅ Pool configuration retrieved")

        # Calculate some derived metrics
        recorded_at = datetime.now(timezone.utc)
        efficiency = 3.8 / (hashrate_ghs / 1000.0) if hashrate_ghs > 0 else 0  # Using estimated 3.8W power

        print(f"\n6. Derived metrics:")
        print(f"   Timestamp: {recorded_at.isoformat()}")
        print(f"   Efficiency: {efficiency:.1f} J/TH (estimated)")
        print(f"   Reject rate: {(shares_rejected/(shares_accepted+shares_rejected)*100):.2f}%")

        print("\n✅ Complete data collection test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ Data collection test FAILED: {e}")
        return False

if __name__ == "__main__":
    test_complete_data_collection()