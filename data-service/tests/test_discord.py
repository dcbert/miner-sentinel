#!/usr/bin/env python3
"""
Test script for Discord webhook notifications
Run this script to test if your Discord webhook is configured correctly.
"""
import os
import sys
from pathlib import Path

# Portable path setup: add data-service root (not tests/ dir) so "from collectors..." and "from notifications..." work
# regardless of cwd, invocation dir, or CI environment.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notifications.discord_notifier import DiscordNotifier


def test_discord_setup():
    """Test Discord notification setup.
    Skipped when DISCORD_WEBHOOK_URL is not configured.
    """
    import pytest

    notifier = DiscordNotifier()

    if not notifier.enabled:
        pytest.skip("Discord webhook not set (DISCORD_WEBHOOK_URL missing) — skipping")

    assert notifier.test_connection(), "Discord webhook test failed — check the URL is valid and accessible"

    # Also test the plain message path
    sent = notifier.send_message("🔧 **Test Message**\n\nDiscord webhook notifications are working correctly for MinerSentinel!")
    assert sent, "Failed to send test message via Discord webhook"


if __name__ == "__main__":
    # Allow direct run without pytest
    notifier = DiscordNotifier()
    if not notifier.enabled:
        print("DISCORD_WEBHOOK_URL not configured. Set it as env var or pass to constructor.")
        sys.exit(1)

    print("Testing Discord webhook connection...")
    success = notifier.test_connection()
    if success:
        print("✅ Test embed sent successfully!")
    else:
        print("❌ Test failed.")
        sys.exit(1)

    # Also plain
    print("Sending plain test message...")
    ok = notifier.send_message("✅ MinerSentinel Discord notifier is operational.")
    if ok:
        print("✅ Plain message sent.")
    else:
        print("⚠️ Plain message may have failed (check logs).")

    sys.exit(0 if success else 1)
