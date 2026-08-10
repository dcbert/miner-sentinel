"""
NerdNOS device collector (GitHub #25).

NerdNOS Metal Edition exposes a small HTTP status API with field names that
differ from AxeOS Bitaxe. Separate make so it is never mixed with bitaxe parsing.

API (sample):
  GET /api/status
  {
    "hashrate_ghs": 196.56,
    "temperature_c": 58.9,
    "hostname": "NerdNOS",
    "bestDifficulty": 23196269,
    "shares_a": 3766,
    "mac": "XX:XX:XX:XX:XX:XX",
    "firmware_version": "2.0.5"
  }
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

import psycopg2
import requests
from collectors.normalized import (
    DeviceDataWriter,
    HardwareMetrics,
    MiningMetrics,
    NormalizedDeviceSnapshot,
    SystemMetrics,
    efficiency_j_per_th,
    parse_difficulty,
    was_device_online,
)
from notifications.discord_notifier import DiscordNotifier
from notifications.rules import NotificationRules
from notifications.telegram_notifier import TelegramNotifier
from retrying import retry

logger = logging.getLogger(__name__)


class NerdNOSCollector:
    """Collects data from NerdNOS devices via GET /api/status."""

    MAKE = 'nerdnos'
    STATUS_ENDPOINTS = ('api/status', 'api/system/status', 'status')

    def __init__(self, database_url, dual_write=False):
        self.database_url = database_url
        self.devices = []
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()
        self.notification_rules = NotificationRules()
        self.writer = DeviceDataWriter(database_url, dual_write=dual_write)

    def update_telegram_settings(self, enabled, bot_token, chat_id):
        if enabled and bot_token and chat_id:
            self.telegram_notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
        else:
            self.telegram_notifier = TelegramNotifier()

    def update_discord_settings(self, enabled, webhook_url):
        if enabled:
            self.discord_notifier = DiscordNotifier(webhook_url=webhook_url if webhook_url else None)
        else:
            self.discord_notifier = DiscordNotifier(webhook_url='')

    def update_notification_rules(self, rules):
        self.notification_rules = NotificationRules(rules)

    def _notify(self, event_key: str, method_name: str, *args, **kwargs):
        if not self.notification_rules.enabled(event_key):
            return
        tg = getattr(self.telegram_notifier, method_name, None)
        dc = getattr(self.discord_notifier, method_name, None)
        if tg:
            tg(*args, **kwargs)
        if dc:
            dc(*args, **kwargs)

    def update_devices(self, devices):
        self.devices = devices
        logger.info(f"Updated NerdNOS device list: {len(devices)} devices")
        for device in devices:
            logger.info(f"  - {device['device_name']} ({device['device_id']}): {device['ip_address']}")

    def get_db_connection(self):
        return psycopg2.connect(self.database_url)

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _api_request(self, ip, endpoint):
        url = f"http://{ip}/{endpoint.lstrip('/')}"
        logger.info(f"Requesting: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def fetch_status(self, device_ip: str) -> Dict[str, Any]:
        """Try known status endpoints; prefer /api/status."""
        last_err = None
        for endpoint in self.STATUS_ENDPOINTS:
            try:
                return self._api_request(device_ip, endpoint)
            except Exception as e:
                last_err = e
                logger.debug(f"NerdNOS endpoint {endpoint} failed: {e}")
        raise last_err or RuntimeError('No NerdNOS status endpoint responded')

    def update_device_status(self, device_id, device_ip, is_online, error_message=""):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT error_message, last_seen_at, name
                FROM devices
                WHERE make = %s AND device_id = %s
                """,
                (self.MAKE, device_id),
            )
            result = cursor.fetchone()
            if not result:
                return
            prev_error, last_seen, device_name = result
            previously_online = was_device_online(prev_error, last_seen)
            self.writer.update_device_status(self.MAKE, device_id, is_online, error_message)

            if previously_online and not is_online:
                last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Unknown"
                self._notify(
                    'device_offline',
                    'send_device_offline_alert',
                    device_id,
                    device_name or device_id,
                    last_seen_str,
                    error_message,
                )
            elif not previously_online and is_online and last_seen is not None:
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                duration = datetime.now(timezone.utc) - last_seen
                total = int(duration.total_seconds())
                duration_str = f"{total // 3600}h {(total % 3600) // 60}m {total % 60}s"
                self._notify(
                    'device_online',
                    'send_device_online_alert',
                    device_id,
                    device_name or device_id,
                    duration_str,
                )
        except Exception as e:
            logger.error(f"Error updating NerdNOS device status for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def check_hashrate_stagnation(self, device_db_id, device_id, device_name, current_hashrate, device_ip):
        stagnation_on = self.notification_rules.enabled('hashrate_stagnation')
        if not stagnation_on:
            return
        threshold = int(self.notification_rules.get('hashrate_stagnation', 'threshold_collections', 3) or 3)
        threshold = max(2, min(20, threshold))
        tolerance = float(self.notification_rules.get('hashrate_stagnation', 'tolerance_ghs', 0.1) or 0.1)
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT hashrate_ghs FROM device_mining_stats
                WHERE device_id = %s
                ORDER BY recorded_at DESC
                LIMIT %s
                """,
                (device_db_id, threshold),
            )
            recent = [row[0] for row in cursor.fetchall()]
            if len(recent) >= threshold and all(
                abs((hr or 0) - (recent[0] or 0)) < tolerance for hr in recent
            ):
                logger.warning(f"Hashrate stagnation detected for NerdNOS {device_id}")
                self._notify(
                    'hashrate_stagnation',
                    'send_hashrate_alert',
                    device_id,
                    device_name,
                    current_hashrate,
                    threshold,
                )
                # No remote restart API documented for NerdNOS
        except Exception as e:
            logger.error(f"Error checking hashrate stagnation for NerdNOS {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def check_best_difficulty_improvement(self, device_db_id, device_id, device_name, current_best_diff):
        if not self.notification_rules.enabled('best_difficulty'):
            return
        min_improvement = float(
            self.notification_rules.get('best_difficulty', 'min_improvement_percent', 5.0) or 5.0
        )
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT best_difficulty FROM device_mining_stats
                WHERE device_id = %s AND best_difficulty IS NOT NULL AND best_difficulty > 0
                ORDER BY recorded_at DESC
                LIMIT 1 OFFSET 1
                """,
                (device_db_id,),
            )
            row = cursor.fetchone()
            previous_best = float(row[0]) if row and row[0] else 0.0
            if current_best_diff > 0 and previous_best > 0:
                improvement = ((current_best_diff - previous_best) / previous_best) * 100
                if improvement >= min_improvement:
                    self._notify(
                        'best_difficulty',
                        'send_best_difficulty_alert',
                        device_id,
                        device_name,
                        current_best_diff,
                        previous_best,
                    )
        except Exception as e:
            logger.error(f"Error checking best difficulty for NerdNOS {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def normalize_status(self, data: Dict[str, Any], device_id: str) -> NormalizedDeviceSnapshot:
        """Map NerdNOS /api/status fields to canonical snapshot."""
        # Accept a few alias spellings seen in forks
        hashrate_ghs = float(
            data.get('hashrate_ghs')
            or data.get('hashRate')
            or data.get('hashrate')
            or 0
        )
        temperature_c = float(
            data.get('temperature_c')
            or data.get('temp')
            or data.get('temperature')
            or 0
        )
        best_diff = parse_difficulty(
            data.get('bestDifficulty')
            or data.get('best_difficulty')
            or data.get('bestDiff')
            or 0
        )
        shares_accepted = int(
            data.get('shares_a')
            or data.get('sharesAccepted')
            or data.get('shares_accepted')
            or 0
        )
        shares_rejected = int(
            data.get('shares_r')
            or data.get('sharesRejected')
            or data.get('shares_rejected')
            or 0
        )
        power_watts = data.get('power_watts') or data.get('power')
        power_watts = float(power_watts) if power_watts is not None else None
        uptime = int(data.get('uptime_seconds') or data.get('uptimeSeconds') or 0)

        details = {
            'api_shape': 'nerdnos_status',
            'raw_keys': sorted(str(k) for k in data.keys()),
        }
        # Keep unknown scalar extras for future UI
        for key, val in data.items():
            if key not in details and not isinstance(val, (dict, list)):
                details[f'extra_{key}'] = val

        return NormalizedDeviceSnapshot(
            make=self.MAKE,
            device_id=device_id,
            recorded_at=datetime.now(timezone.utc),
            online=True,
            mining=MiningMetrics(
                hashrate_ghs=hashrate_ghs,
                shares_accepted=shares_accepted,
                shares_rejected=shares_rejected,
                uptime_seconds=uptime,
                best_difficulty=best_diff,
                best_session_difficulty=parse_difficulty(
                    data.get('bestSessionDifficulty') or data.get('bestSessionDiff') or 0
                ) or None,
                pool_url=data.get('pool_url') or data.get('stratumURL'),
                pool_user=data.get('pool_user') or data.get('stratumUser'),
            ),
            hardware=HardwareMetrics(
                temperature_c=temperature_c,
                power_watts=power_watts,
                efficiency_j_per_th=efficiency_j_per_th(power_watts, hashrate_ghs),
                fan_speed_rpm=int(data.get('fan_rpm') or data.get('fanrpm') or 0) or None,
                voltage=float(data.get('voltage')) if data.get('voltage') is not None else None,
                frequency_mhz=float(data.get('frequency')) if data.get('frequency') is not None else None,
            ),
            system=SystemMetrics(
                hostname=data.get('hostname') or data.get('hostName') or 'NerdNOS',
                mac_address=data.get('mac') or data.get('macAddr'),
                firmware_version=data.get('firmware_version') or data.get('version'),
                model_reported=data.get('model') or data.get('hwModel') or 'NerdNOS',
                wifi_ssid=data.get('ssid'),
                wifi_rssi=data.get('rssi') or data.get('wifiRSSI'),
                details=details,
            ),
        )

    def collect_device_data(self, device_id, device_ip):
        try:
            status = self.fetch_status(device_ip)
            snapshot = self.normalize_status(status, device_id)

            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name FROM devices WHERE make = %s AND device_id = %s",
                (self.MAKE, device_id),
            )
            device_row = cursor.fetchone()
            device_name = device_row[1] if device_row else device_id
            cursor.close()
            conn.close()

            device_db_id = self.writer.write_snapshot(snapshot)
            self.update_device_status(device_id, device_ip, True)

            if device_db_id and snapshot.mining:
                self.check_hashrate_stagnation(
                    device_db_id, device_id, device_name,
                    snapshot.mining.hashrate_ghs, device_ip,
                )
                self.check_best_difficulty_improvement(
                    device_db_id, device_id, device_name,
                    snapshot.mining.best_difficulty or 0,
                )

            logger.info(
                f"Collected NerdNOS data from {device_id} - "
                f"Hashrate: {snapshot.mining.hashrate_ghs:.2f} GH/s, "
                f"Temp: {snapshot.hardware.temperature_c}°C"
            )
        except Exception as e:
            logger.error(f"Error collecting NerdNOS data from {device_id} ({device_ip}): {e}", exc_info=True)
            self.update_device_status(device_id, device_ip, False, str(e))

    def collect_all_devices(self):
        if not self.devices:
            logger.warning("No NerdNOS devices configured for collection")
            return
        for device in self.devices:
            logger.info(f"Collecting data for NerdNOS device: {device['device_id']} at {device['ip_address']}")
            self.collect_device_data(device['device_id'], device['ip_address'])
