#!/usr/bin/env python3
"""
Test script for Telegram notifications
Run this script to test if your Telegram bot is configured correctly.
"""

import os
import sys
from pathlib import Path

# Add the data-service directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from notifications.telegram_notifier import TelegramNotifier


def test_telegram_setup():
    """Test Telegram notification setup."""
    print("Testing Telegram notification setup...")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("❌ Telegram notifications are disabled.")
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
        print("See .env.example for configuration instructions.")
        return False

    print("✅ Telegram credentials found. Testing connection...")

    if notifier.test_connection():
        print("✅ Telegram bot connection successful!")

        # Send a test message
        print("Sending test message...")
        if notifier.send_message("🔧 <b>Test Message</b>\n\nTelegram notifications are working correctly for MinerSentinel mining alerts!"):
            print("✅ Test message sent successfully!")

            # Test alert messages
            print("Testing alert message formats...")
            notifier.send_hashrate_alert("bitaxe_1", "Test Bitaxe", 450.5, 3)
            notifier.send_best_difficulty_alert("bitaxe_1", "Test Bitaxe", 25.6e6, 22.3e6)
            notifier.send_device_offline_alert("bitaxe_1", "Test Bitaxe", "2024-10-23 10:30:00", "Connection timeout")
            notifier.send_device_online_alert("bitaxe_1", "Test Bitaxe", "2h 15m 30s")
            notifier.send_device_restart_notification("bitaxe_1", "Test Bitaxe")

            print("✅ All tests completed successfully!")
            return True
        else:
            print("❌ Failed to send test message.")
            return False
    else:
        print("❌ Telegram bot connection failed.")
        print("Please check your bot token and ensure the bot is started.")
        return False


if __name__ == "__main__":
    success = test_telegram_setup()
    sys.exit(0 if success else 1)