"""
Telegram notification service
"""

import html
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Handles Telegram notifications for mining alerts."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        # Debug logging for configuration
        logger.info(f"Telegram bot token configured: {bool(self.bot_token)}")
        logger.info(f"Telegram chat ID configured: {bool(self.chat_id)}")
        if self.bot_token:
            logger.info(f"Bot token length: {len(self.bot_token)} characters")
        if self.chat_id:
            logger.info(f"Chat ID: {self.chat_id}")

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not configured. Notifications disabled.")
            logger.warning(f"Bot token present: {bool(self.bot_token)}")
            logger.warning(f"Chat ID present: {bool(self.chat_id)}")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram notifier initialized and enabled")

    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to Telegram chat."""
        if not self.enabled:
            logger.debug(f"Telegram disabled. Would send: {message}")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            response = requests.post(url, json=payload, timeout=10)

            # Log the complete response for debugging
            logger.info(f"Telegram API response status: {response.status_code}")
            logger.info(f"Telegram API response body: {response.text}")

            response.raise_for_status()

            logger.info(f"Telegram message sent successfully")
            return True

        except requests.exceptions.HTTPError as e:
            # If it's a 400 error with HTML parsing issues, try sending as plain text
            if response.status_code == 400 and parse_mode == 'HTML' and 'parse entities' in response.text:
                logger.warning("HTML parsing failed, retrying with plain text...")
                return self.send_message(message, parse_mode='')

            logger.error(f"HTTP error from Telegram API: {e}")
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response body: {response.text}")
            logger.error(f"Request URL: {url}")
            logger.error(f"Request payload: {payload}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_hashrate_alert(self, device_id: str, device_name: str, hashrate: float, collections_count: int):
        """Send hashrate stagnation alert."""
        message = (
            f"🚨 <b>Mining Alert</b>\n\n"
            f"<b>Device:</b> {html.escape(device_name)} ({html.escape(device_id)})\n"
            f"<b>Issue:</b> Hashrate unchanged for {collections_count} collections\n"
            f"<b>Current Hashrate:</b> {hashrate:.2f} GH/s\n\n"
            f"⚠️ Device may need attention"
        )
        return self.send_message(message)

    def send_best_difficulty_alert(self, device_id: str, device_name: str, new_best: float, previous_best: float):
        """Send new best difficulty achievement alert."""
        improvement = ((new_best - previous_best) / previous_best) * 100 if previous_best > 0 else 0

        message = (
            f"🎉 <b>New Best Difficulty!</b>\n\n"
            f"<b>Device:</b> {html.escape(device_name)} ({html.escape(device_id)})\n"
            f"<b>New Best:</b> {self._format_difficulty(new_best)}\n"
            f"<b>Previous Best:</b> {self._format_difficulty(previous_best)}\n"
        )

        if improvement > 0:
            message += f"<b>Improvement:</b> +{improvement:.1f}%\n"

        message += "\n🔥 Keep it up!"

        return self.send_message(message)

    def send_device_offline_alert(self, device_id: str, device_name: str, last_seen: str, error_message: str = ""):
        """Send device offline alert."""
        message = (
            f"🔴 <b>Device Offline Alert</b>\n\n"
            f"<b>Device:</b> {html.escape(device_name)} ({html.escape(device_id)})\n"
            f"<b>Status:</b> Unable to connect\n"
            f"<b>Last Seen:</b> {html.escape(last_seen)}\n"
        )

        if error_message:
            # Escape HTML characters in error message to prevent parsing issues
            escaped_error = html.escape(error_message)
            message += f"<b>Error:</b> {escaped_error}\n"

        message += "\n⚠️ Please check device connectivity"

        return self.send_message(message)

    def send_device_online_alert(self, device_id: str, device_name: str, offline_duration: str):
        """Send device back online alert."""
        message = (
            f"🟢 <b>Device Back Online</b>\n\n"
            f"<b>Device:</b> {html.escape(device_name)} ({html.escape(device_id)})\n"
            f"<b>Status:</b> Connection restored\n"
            f"<b>Offline Duration:</b> {html.escape(offline_duration)}\n\n"
            f"✅ Device is collecting data again"
        )

        return self.send_message(message)

    def send_device_restart_notification(self, device_id: str, device_name: str):
        """Send device restart notification."""
        message = (
            f"🔄 <b>Device Restart</b>\n\n"
            f"<b>Device:</b> {html.escape(device_name)} ({html.escape(device_id)})\n"
            f"<b>Reason:</b> Hashrate stagnation detected\n"
            f"<b>Action:</b> Automatic restart initiated\n\n"
            f"⚡ Device should resume normal operation shortly"
        )

        return self.send_message(message)

    def _format_difficulty(self, difficulty: float) -> str:
        """Format difficulty value with appropriate unit."""
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
        """Test Telegram bot connection."""
        if not self.enabled:
            return False

        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)

            # Log the complete response for debugging
            logger.info(f"Telegram getMe response status: {response.status_code}")
            logger.info(f"Telegram getMe response body: {response.text}")

            response.raise_for_status()
            bot_info = response.json()

            if bot_info.get('ok'):
                logger.info(f"Telegram bot connected: {bot_info['result']['username']}")
                return True
            else:
                logger.error(f"Telegram bot test failed: {bot_info}")
                return False

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during Telegram connection test: {e}")
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response body: {response.text}")
            logger.error(f"Request URL: {url}")
            return False
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False