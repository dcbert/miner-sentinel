#!/usr/bin/env python3
"""
Test script for Avalon Nano 3s socket API communication
"""

import socket
import time


def test_avalon_api(ip, port=4028):
    """Test the Avalon cgminer socket API."""
    commands = ['version', 'summary', 'estats', 'pools']

    print(f"Testing Avalon API at {ip}:{port}")
    print("=" * 50)

    for command in commands:
        print(f"\n--- Testing command: {command} ---")
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((ip, port))

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

            sock.close()

            # Parse and display response
            response_str = response.decode('utf-8', errors='ignore').strip()
            print(f"Raw response: {response_str}")

            # Parse key-value pairs
            parts = response_str.split('|')
            parsed_data = {}

            for part in parts:
                if '=' in part and ',' in part:
                    pairs = part.split(',')
                    for pair in pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            parsed_data[key.strip()] = value.strip()
                elif '=' in part:
                    key, value = part.split('=', 1)
                    parsed_data[key.strip()] = value.strip()

            print(f"Parsed data keys: {list(parsed_data.keys())}")

            # Show all key-value pairs for debugging
            if command == 'estats':
                print("All estats data:")
                for key, value in parsed_data.items():
                    print(f"  {key}: {value}")

            # Show some key values for each command
            if command == 'summary':
                print(f"  Hashrate (MHS av): {parsed_data.get('MHS av', 'N/A')}")
                print(f"  Accepted shares: {parsed_data.get('Accepted', 'N/A')}")
                print(f"  Rejected shares: {parsed_data.get('Rejected', 'N/A')}")
                print(f"  Uptime: {parsed_data.get('Elapsed', 'N/A')} seconds")
            elif command == 'version':
                print(f"  Product: {parsed_data.get('PROD', 'N/A')}")
                print(f"  Model: {parsed_data.get('MODEL', 'N/A')}")
                print(f"  CGMiner: {parsed_data.get('CGMiner', 'N/A')}")
                print(f"  MAC: {parsed_data.get('MAC', 'N/A')}")
            elif command == 'estats':
                print(f"  Temperature (OTemp): {parsed_data.get('OTemp', 'N/A')}")
                print(f"  Fan speed: {parsed_data.get('Fan1', 'N/A')}")
                print(f"  Frequency: {parsed_data.get('Freq', 'N/A')}")
                print(f"  Memory free: {parsed_data.get('MEMFREE', 'N/A')}")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)  # Wait between commands

if __name__ == "__main__":
    # Test with example IP - replace with your Avalon device IP
    test_ip = "192.168.1.100"  # Replace with your Avalon device IP

    print("Avalon Nano 3s API Test")
    print("Make sure your device is accessible and cgminer API is enabled")
    print(f"Testing with IP: {test_ip}")

    test_avalon_api(test_ip)