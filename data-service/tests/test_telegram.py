#!/usr/bin/env python3
"""
Test script for Telegram notifications
Run this script to test if your Telegram bot is configured correctly.
"""

import os
import sys
from pathlib import Path

# Portable path setup: add data-service root (not tests/ dir) so "from collectors..." and "from notifications..." work
# regardless of cwd, invocation dir, or CI environment. (Previously used .parent which pointed inside tests/.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notifications.telegram_notifier import TelegramNotifier


def test_telegram_setup():
    """Test Telegram notification setup.
    Skipped when TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not configured.
    """
    import pytest

    notifier = TelegramNotifier()

    if not notifier.enabled:
        pytest.skip("Telegram credentials not set (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing) — skipping")

    assert notifier.test_connection(), "Telegram bot connection failed — check token and chat ID"

    sent = notifier.send_message("🔧 <b>Test Message</b>\n\nTelegram notifications are working correctly for MinerSentinel!")
    assert sent, "Failed to send test message via Telegram"

if __name__ == "__main__":
    test_telegram_setup()
    sys.exit(0 if success else 1)