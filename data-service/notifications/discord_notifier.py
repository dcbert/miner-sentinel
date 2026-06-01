"""
Discord webhook notification service for MinerSentinel alerts.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Handles Discord webhook notifications for mining alerts using rich embeds."""

    # Embed colors (decimal)
    COLOR_ALERT = 15158332      # Red for problems (offline, stagnation, restart)
    COLOR_SUCCESS = 3066993     # Green for recovery (online)
    COLOR_ACHIEVEMENT = 15844367  # Gold for best difficulty

    def __init__(self, webhook_url: Optional[str] = None):
        # Only fall back to the environment when webhook_url is not explicitly provided.
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL') if webhook_url is None else webhook_url

        logger.info(f"Discord webhook configured: {bool(self.webhook_url)}")

        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured. Notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Discord notifier initialized and enabled")

    def send_embed(self, embed: dict) -> bool:
        """Send a rich embed to Discord webhook."""
        if not self.enabled:
            logger.debug(f"Discord disabled. Would send embed: {embed.get('title', 'untitled')}")
            return False

        try:
            payload = {
                "username": "MinerSentinel",
                "embeds": [embed]
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)

            logger.info(f"Discord webhook response status: {response.status_code}")

            # Discord returns 204 No Content on success
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
                return True
            elif response.status_code == 429:
                logger.warning("Discord rate limit hit")
                return False
            else:
                logger.error(f"Discord webhook error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def send_message(self, content: str) -> bool:
        """Send a plain text message (fallback/simple notifications)."""
        if not self.enabled:
            logger.debug(f"Discord disabled. Would send: {content}")
            return False

        try:
            payload = {
                "username": "MinerSentinel",
                "content": content
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)

            if response.status_code == 204:
                logger.info("Discord message sent successfully")
                return True
            else:
                logger.error(f"Discord message error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False

    def send_hashrate_alert(self, device_id: str, device_name: str, hashrate: float, collections_count: int):
        """Send hashrate stagnation alert as Discord embed."""
        embed = {
            "title": "🚨 Mining Alert - Hashrate Stagnation",
            "description": "Device hashrate has been unchanged for multiple collection cycles.",
            "color": self.COLOR_ALERT,
            "fields": [
                {
                    "name": "Device",
                    "value": f"**{device_name}** (`{device_id}`)",
                    "inline": True
                },
                {
                    "name": "Current Hashrate",
                    "value": f"{hashrate:.2f} GH/s",
                    "inline": True
                },
                {
                    "name": "Stagnation Duration",
                    "value": f"{collections_count} collections",
                    "inline": True
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "MinerSentinel Alert System"
            }
        }
        return self.send_embed(embed)

    def send_best_difficulty_alert(self, device_id: str, device_name: str, new_best: float, previous_best: float):
        """Send new best difficulty achievement alert as Discord embed."""
        improvement = ((new_best - previous_best) / previous_best) * 100 if previous_best > 0 else 0

        fields = [
            {
                "name": "Device",
                "value": f"**{device_name}** (`{device_id}`)",
                "inline": True
            },
            {
                "name": "New Best",
                "value": self._format_difficulty(new_best),
                "inline": True
            }
        ]

        if previous_best > 0:
            fields.append({
                "name": "Previous Best",
                "value": self._format_difficulty(previous_best),
                "inline": True
            })
            fields.append({
                "name": "Improvement",
                "value": f"+{improvement:.1f}%",
                "inline": True
            })
        else:
            fields.append({
                "name": "Status",
                "value": "First recorded best share!",
                "inline": True
            })

        embed = {
            "title": "🎉 New Best Difficulty Achievement!",
            "description": "Congratulations! The device achieved a new personal best.",
            "color": self.COLOR_ACHIEVEMENT,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "MinerSentinel • Keep it up!"
            }
        }
        return self.send_embed(embed)

    def send_device_offline_alert(self, device_id: str, device_name: str, last_seen: str, error_message: str = ""):
        """Send device offline alert as Discord embed."""
        fields = [
            {
                "name": "Device",
                "value": f"**{device_name}** (`{device_id}`)",
                "inline": True
            },
            {
                "name": "Status",
                "value": "🔴 Unable to connect",
                "inline": True
            },
            {
                "name": "Last Seen",
                "value": last_seen,
                "inline": True
            }
        ]

        if error_message:
            # Truncate long error messages
            err = error_message[:200] + "..." if len(error_message) > 200 else error_message
            fields.append({
                "name": "Error Details",
                "value": f"```{err}```",
                "inline": False
            })

        embed = {
            "title": "🔴 Device Offline Alert",
            "description": "A mining device has gone offline and is no longer reachable.",
            "color": self.COLOR_ALERT,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "MinerSentinel • Check device connectivity"
            }
        }
        return self.send_embed(embed)

    def send_device_online_alert(self, device_id: str, device_name: str, offline_duration: str):
        """Send device back online alert as Discord embed."""
        embed = {
            "title": "🟢 Device Back Online",
            "description": "Connection to the device has been restored.",
            "color": self.COLOR_SUCCESS,
            "fields": [
                {
                    "name": "Device",
                    "value": f"**{device_name}** (`{device_id}`)",
                    "inline": True
                },
                {
                    "name": "Offline Duration",
                    "value": offline_duration,
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": "✅ Collecting data again",
                    "inline": True
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "MinerSentinel"
            }
        }
        return self.send_embed(embed)

    def send_device_restart_notification(self, device_id: str, device_name: str):
        """Send device restart notification as Discord embed."""
        embed = {
            "title": "🔄 Device Restart Initiated",
            "description": "Automatic restart triggered due to hashrate stagnation detection.",
            "color": self.COLOR_ALERT,
            "fields": [
                {
                    "name": "Device",
                    "value": f"**{device_name}** (`{device_id}`)",
                    "inline": True
                },
                {
                    "name": "Action",
                    "value": "Automatic restart sent to device",
                    "inline": True
                },
                {
                    "name": "Expected Outcome",
                    "value": "Device should resume normal operation shortly",
                    "inline": False
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "MinerSentinel • Monitoring recovery"
            }
        }
        return self.send_embed(embed)

    def _format_difficulty(self, difficulty: float) -> str:
        """Format difficulty value with appropriate unit (same as Telegram)."""
        if difficulty >= 1e12:
            return f"{difficulty/1e12:.2f} T"
        elif difficulty >= 1e9:
            return f"{difficulty/1e9:.2f} G"
        elif difficulty >= 1e6:
            return f"{difficulty/1e6:.2f} M"
        elif difficulty >= 1e3:
            return f"{difficulty/1e3:.2f} K"
        else:
            return f"{difficulty:.2f}"

    def test_connection(self) -> bool:
        """Test Discord webhook by sending a test embed."""
        if not self.enabled:
            return False

        try:
            embed = {
                "title": "🔧 Test Notification",
                "description": "Discord webhook notifications are working correctly for MinerSentinel!",
                "color": 3447003,  # Blue
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {
                    "text": "MinerSentinel Test"
                }
            }
            return self.send_embed(embed)

        except Exception as e:
            logger.error(f"Discord connection test failed: {e}")
            return False
