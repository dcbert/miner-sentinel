"""
NMAxe / NMAxeGamma device collector (GitHub #14).

NMAxe is a Bitaxe-derived fork (NMTech) with a nested AxeOS-style JSON API.
Kept as a separate make so firmware divergence does not break original Bitaxe.

API:
  GET  /api/system/info   — nested { miner, temps, power, asic, identity, stratum, fans }
  POST /api/system/restart
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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


class NMAxeCollector:
    """Collects data from NMAxe / NMAxeGamma devices (nested /api/system/info)."""

    MAKE = 'nmaxe'

    def __init__(self, database_url):
        self.database_url = database_url
        self.devices = []
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()
        self.notification_rules = NotificationRules()
        self.writer = DeviceDataWriter(database_url)

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
        logger.info(f"Updated NMAxe device list: {len(devices)} devices")
        for device in devices:
            logger.info(f"  - {device['device_name']} ({device['device_id']}): {device['ip_address']}")

    def get_db_connection(self):
        return psycopg2.connect(self.database_url)

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _api_request(self, ip, endpoint):
        url = f"http://{ip}/{endpoint}"
        logger.info(f"Requesting: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def restart_device(self, device_ip, device_id, device_name):
        try:
            url = f"http://{device_ip}/api/system/restart"
            logger.info(f"Attempting to restart NMAxe device {device_id} at {url}")
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent restart command to NMAxe device {device_id}")
            self._notify(
                'auto_restart',
                'send_device_restart_notification',
                device_id,
                device_name,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to restart NMAxe device {device_id} ({device_ip}): {e}")
            return False

    def check_hashrate_stagnation(self, device_db_id, device_id, device_name, current_hashrate, device_ip):
        stagnation_on = self.notification_rules.enabled('hashrate_stagnation')
        restart_on = self.notification_rules.enabled('auto_restart')
        if not stagnation_on and not restart_on:
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
                logger.warning(f"Hashrate stagnation detected for NMAxe {device_id}")
                if stagnation_on:
                    self._notify(
                        'hashrate_stagnation',
                        'send_hashrate_alert',
                        device_id,
                        device_name,
                        current_hashrate,
                        threshold,
                    )
                if restart_on:
                    self.restart_device(device_ip, device_id, device_name)
        except Exception as e:
            logger.error(f"Error checking hashrate stagnation for NMAxe {device_id}: {e}")
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
            logger.error(f"Error checking best difficulty for NMAxe {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

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
            logger.error(f"Error updating NMAxe device status for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def normalize_system_info(self, data: Dict[str, Any], device_id: str) -> NormalizedDeviceSnapshot:
        """
        Convert nested NMAxe /api/system/info JSON into NormalizedDeviceSnapshot.

        Also tolerates a flat Bitaxe-like payload if present (defensive).
        """
        # Nested NMAxe v3+ shape
        if isinstance(data.get('miner'), dict) or isinstance(data.get('identity'), dict):
            miner = data.get('miner') or {}
            temps = data.get('temps') or {}
            power_obj = data.get('power') or {}
            asic = data.get('asic') or {}
            identity = data.get('identity') or {}
            stratum = data.get('stratum') or {}
            fans = data.get('fans') or []
            fan0 = fans[0] if fans and isinstance(fans[0], dict) else {}

            hashrate_ghs = float(miner.get('hashRate', 0) or 0)
            best_ever = parse_difficulty(miner.get('bestDiffEver', 0))
            best_session = parse_difficulty(miner.get('bestDiffSession', 0))
            power_watts = float(power_obj.get('power', 0) or 0)
            temp_c = float(temps.get('asic', 0) or 0)
            vcore_mv = asic.get('vcoreReal') or asic.get('vcoreReq') or 0
            voltage = float(vcore_mv or 0) / 1000.0
            frequency = float(asic.get('freqReq', 0) or 0)
            fan_rpm = int(fan0.get('rpm', 0) or 0)
            fan_pct = fan0.get('speed')

            details = {
                'api_shape': 'nmaxe_nested',
                'hw_model': identity.get('hwModel'),
                'display_name': identity.get('displayName'),
                'fw_version': identity.get('fwVersion'),
                'app_sha256': identity.get('appSha256'),
                'asic_model': asic.get('model'),
                'asic_count': asic.get('count'),
                'small_core_count': asic.get('smallCoreCnt'),
                'vcore_req': asic.get('vcoreReq'),
                'vcore_real': asic.get('vcoreReal'),
                'vbus': power_obj.get('vbus'),
                'ibus': power_obj.get('ibus'),
                'temp_vcore': temps.get('vcore'),
                'pool_diff': miner.get('poolDiff'),
                'network_diff': miner.get('networkDiff'),
                'last_diff': miner.get('lastDiff'),
                'blkhits': miner.get('blkhits'),
                'free_heap': miner.get('freeHeap') or miner.get('minFreeHeap'),
                'min_free_heap': miner.get('minFreeHeap'),
                'uptime_ever': miner.get('uptimeEver'),
                'fans': fans,
                'raw_stratum_pwd_present': bool(stratum.get('pwd')),
            }

            return NormalizedDeviceSnapshot(
                make=self.MAKE,
                device_id=device_id,
                recorded_at=datetime.now(timezone.utc),
                online=True,
                mining=MiningMetrics(
                    hashrate_ghs=hashrate_ghs,
                    shares_accepted=int(miner.get('sAccepted', 0) or 0),
                    shares_rejected=int(miner.get('sRejected', 0) or 0),
                    blocks_found=int(miner.get('blkhits', 0) or 0),
                    uptime_seconds=int(miner.get('uptimeSeconds', 0) or 0),
                    best_difficulty=best_ever,
                    best_session_difficulty=best_session,
                    pool_url=stratum.get('url'),
                    pool_user=stratum.get('user'),
                ),
                hardware=HardwareMetrics(
                    temperature_c=temp_c,
                    temperature_chip_c=temp_c,
                    temperature_board_c=float(temps.get('vcore') or 0) or None,
                    power_watts=power_watts,
                    efficiency_j_per_th=efficiency_j_per_th(power_watts, hashrate_ghs),
                    fan_speed_rpm=fan_rpm,
                    fan_speed_percent=int(fan_pct) if fan_pct is not None else None,
                    voltage=voltage,
                    frequency_mhz=frequency,
                ),
                system=SystemMetrics(
                    hostname=identity.get('hostName'),
                    mac_address=None,
                    firmware_version=identity.get('fwVersion'),
                    model_reported=identity.get('hwModel') or asic.get('model'),
                    primary_pool_url=stratum.get('url'),
                    primary_pool_user=stratum.get('user'),
                    wifi_ssid=identity.get('ssid'),
                    wifi_rssi=identity.get('rssi'),
                    details=details,
                ),
            )

        # Flat fallback (unlikely for nmaxe, but safe)
        hashrate_ghs = float(data.get('hashRate', 0) or 0)
        power_watts = float(data.get('power', 0) or 0) if not isinstance(data.get('power'), dict) else 0.0
        return NormalizedDeviceSnapshot(
            make=self.MAKE,
            device_id=device_id,
            recorded_at=datetime.now(timezone.utc),
            online=True,
            mining=MiningMetrics(
                hashrate_ghs=hashrate_ghs,
                shares_accepted=int(data.get('sharesAccepted', 0) or 0),
                shares_rejected=int(data.get('sharesRejected', 0) or 0),
                uptime_seconds=int(data.get('uptimeSeconds', 0) or 0),
                best_difficulty=parse_difficulty(data.get('bestDiff', 0)),
                best_session_difficulty=parse_difficulty(data.get('bestSessionDiff', 0)),
                pool_url=data.get('stratumURL'),
                pool_user=data.get('stratumUser'),
            ),
            hardware=HardwareMetrics(
                temperature_c=float(data.get('temp', 0) or 0),
                power_watts=power_watts,
                efficiency_j_per_th=efficiency_j_per_th(power_watts, hashrate_ghs),
                fan_speed_rpm=int(data.get('fanrpm', 0) or 0),
            ),
            system=SystemMetrics(
                hostname=data.get('hostname'),
                firmware_version=data.get('version'),
                model_reported=data.get('ASICModel') or 'NMAxe',
                details={'api_shape': 'flat_fallback'},
            ),
        )

    def collect_device_data(self, device_id, device_ip):
        try:
            system_info = self._api_request(device_ip, 'api/system/info')
            snapshot = self.normalize_system_info(system_info, device_id)

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
                f"Collected NMAxe data from {device_id} - "
                f"Hashrate: {snapshot.mining.hashrate_ghs:.2f} GH/s, "
                f"Temp: {snapshot.hardware.temperature_c}°C"
            )
        except Exception as e:
            logger.error(f"Error collecting NMAxe data from {device_id} ({device_ip}): {e}", exc_info=True)
            self.update_device_status(device_id, device_ip, False, str(e))

    def collect_all_devices(self):
        if not self.devices:
            logger.warning("No NMAxe devices configured for collection")
            return
        for device in self.devices:
            logger.info(f"Collecting data for NMAxe device: {device['device_id']} at {device['ip_address']}")
            self.collect_device_data(device['device_id'], device['ip_address'])
