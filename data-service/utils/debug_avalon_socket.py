#!/usr/bin/env python3
"""
Debug the Avalon collector to see why it's returning 0 values
"""

import json
import logging
import socket

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_avalon_socket_debug():
    """Test socket communication with detailed debugging."""
    device_ip = "192.168.1.100"  # Replace with your Avalon device IP
    port = 4028

    print(f"🔍 Debugging Avalon socket communication with {device_ip}:{port}")
    print("=" * 60)

    try:
        # Test each command individually
        commands = ['version', 'summary', 'estats', 'pools']

        for command in commands:
            print(f"\n📡 Testing command: {command}")
            print("-" * 30)

            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)

            try:
                # Connect
                print(f"   Connecting to {device_ip}:{port}...")
                sock.connect((device_ip, port))
                print("   ✅ Connected")

                # Send command
                cmd_json = json.dumps({"command": command})
                print(f"   Sending: {cmd_json}")
                sock.send(cmd_json.encode('utf-8'))
                print("   ✅ Command sent")

                # Read response
                response = b""
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                        print(f"   Received chunk: {len(chunk)} bytes")
                    except socket.timeout:
                        print("   Socket timeout - ending read")
                        break

                print(f"   Total response: {len(response)} bytes")

                if response:
                    # Decode response
                    response_str = response.decode('utf-8', errors='ignore').strip()
                    response_str = response_str.replace('\x00', '')

                    print(f"   Raw response length: {len(response_str)}")
                    print(f"   Raw response preview: {response_str[:200]}...")

                    # Try JSON parsing
                    try:
                        parsed = json.loads(response_str)
                        print(f"   ✅ JSON parse successful")
                        print(f"   JSON keys: {list(parsed.keys())}")

                        # Extract data based on command
                        data = None
                        if command.upper() in parsed and parsed[command.upper()]:
                            data = parsed[command.upper()][0] if isinstance(parsed[command.upper()], list) else parsed[command.upper()]
                        elif command.lower() == 'version' and 'VERSION' in parsed:
                            data = parsed['VERSION'][0] if parsed['VERSION'] else {}
                        elif command.lower() == 'summary' and 'SUMMARY' in parsed:
                            data = parsed['SUMMARY'][0] if parsed['SUMMARY'] else {}
                        elif command.lower() == 'estats' and 'STATS' in parsed:
                            data = parsed['STATS'][0] if parsed['STATS'] else {}
                        elif command.lower() == 'pools' and 'POOLS' in parsed:
                            data = parsed['POOLS'][0] if parsed['POOLS'] else {}

                        if data:
                            print(f"   ✅ Extracted data keys: {list(data.keys())}")

                            # Show specific data for each command
                            if command == 'version':
                                print(f"   Device: {data.get('PROD', 'Unknown')}")
                            elif command == 'summary':
                                mhs = data.get('MHS av', '0')
                                print(f"   MHS av: {mhs}")
                                print(f"   Hashrate: {float(mhs)/1000.0:.2f} GH/s")
                            elif command == 'estats':
                                mm_id0 = data.get('MM ID0', '')
                                print(f"   MM ID0 length: {len(mm_id0)}")
                                if 'OTemp[' in mm_id0:
                                    print(f"   ✅ Found OTemp in MM ID0")
                                else:
                                    print(f"   ❌ No OTemp found in MM ID0")
                                    print(f"   MM ID0 preview: {mm_id0[:300]}...")
                            elif command == 'pools':
                                print(f"   Pool URL: {data.get('URL', 'Unknown')}")
                        else:
                            print(f"   ❌ No data extracted for {command}")

                    except json.JSONDecodeError as e:
                        print(f"   ❌ JSON parse failed: {e}")
                        print(f"   Raw content: {response_str[:500]}...")

                else:
                    print("   ❌ No response received")

            except Exception as e:
                print(f"   ❌ Error with {command}: {e}")
            finally:
                sock.close()

        print("\n🎯 Debug summary complete!")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_avalon_socket_debug()