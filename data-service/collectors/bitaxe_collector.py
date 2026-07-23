"""
Bitaxe device collector

Fetches AxeOS HTTP API data, normalizes to canonical units, dual-writes
via DeviceDataWriter (unified tables + legacy bitaxe_* tables).
"""

import logging
from datetime import datetime, timezone

import psycopg2
import requests
from collectors.normalized import (
    DeviceDataWriter,
    HardwareMetrics,
    MiningMetrics,
    NormalizedDeviceSnapshot,
    SystemMetrics,
    efficiency_j_per_th,
)
from notifications.discord_notifier import DiscordNotifier
from notifications.telegram_notifier import TelegramNotifier
from retrying import retry

logger = logging.getLogger(__name__)


class BitAxeCollector:
    """Collects data from Bitaxe mining devices."""

    MAKE = 'bitaxe'

    def __init__(self, database_url, dual_write=False):
        self.database_url = database_url
        self.devices = []  # Will be populated from database
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()
        self.writer = DeviceDataWriter(database_url, dual_write=dual_write)

    def update_telegram_settings(self, enabled, bot_token, chat_id):
        """Update telegram notification settings."""
        logger.info(f"Updating telegram settings: enabled={enabled}")
        if enabled and bot_token and chat_id:
            self.telegram_notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
            logger.info("Telegram notifier enabled with settings from database")
        else:
            self.telegram_notifier = TelegramNotifier()  # Disabled
            logger.info("Telegram notifier disabled")

    def update_discord_settings(self, enabled, webhook_url):
        """Update Discord webhook notification settings."""
        logger.info(f"Updating Discord settings: enabled={enabled}")
        if enabled:
            effective_url = webhook_url if webhook_url else None
            self.discord_notifier = DiscordNotifier(webhook_url=effective_url)
            logger.info("Discord notifier enabled" if self.discord_notifier.enabled else "Discord notifier disabled (no webhook configured)")
        else:
            # Force-disable even if DISCORD_WEBHOOK_URL is set in the environment.
            self.discord_notifier = DiscordNotifier(webhook_url='')
            logger.info("Discord notifier disabled")

    def update_devices(self, devices):
        """Update the list of devices to monitor from database."""
        self.devices = devices
        logger.info(f"Updated Bitaxe device list: {len(devices)} devices")
        for device in devices:
            logger.info(f"  - {device['device_name']} ({device['device_id']}): {device['ip_address']}")

    def get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.database_url)

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _api_request(self, ip, endpoint):
        """Make API request to Bitaxe device with retry logic."""
        url = f"http://{ip}/{endpoint}"
        logger.info(f"Requesting: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def restart_device(self, device_ip, device_id, device_name):
        """Restart a Bitaxe device via API."""
        try:
            url = f"http://{device_ip}/api/system/restart"
            logger.info(f"Attempting to restart device {device_id} at {url}")

            # Make POST request to restart endpoint
            response = requests.post(url, timeout=10)
            response.raise_for_status()

            logger.info(f"Successfully sent restart command to device {device_id}")

            # Send notification about the restart
            self.telegram_notifier.send_device_restart_notification(
                device_id, device_name
            )
            self.discord_notifier.send_device_restart_notification(
                device_id, device_name
            )

            return True

        except Exception as e:
            logger.error(f"Failed to restart device {device_id} ({device_ip}): {e}")
            return False

    def check_hashrate_stagnation(self, device_db_id, device_id, device_name, current_hashrate, device_ip):
        """Check if hashrate has been unchanged for 3 collections (unified table)."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT hashrate_ghs
                FROM device_mining_stats
                WHERE device_id = %s
                ORDER BY recorded_at DESC
                LIMIT 3
            """, (device_db_id,))

            recent_hashrates = [row[0] for row in cursor.fetchall()]

            if len(recent_hashrates) >= 3:
                if all(abs(hr - recent_hashrates[0]) < 0.1 for hr in recent_hashrates):
                    logger.warning(f"Hashrate stagnation detected for {device_id}")
                    self.telegram_notifier.send_hashrate_alert(
                        device_id, device_name, current_hashrate, 3
                    )
                    self.discord_notifier.send_hashrate_alert(
                        device_id, device_name, current_hashrate, 3
                    )
                    logger.info(f"Attempting automatic restart for device {device_id} due to hashrate stagnation")
                    self.restart_device(device_ip, device_id, device_name)

        except Exception as e:
            logger.error(f"Error checking hashrate stagnation for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def check_best_difficulty_improvement(self, device_db_id, device_id, device_name, current_best_diff):
        """Check if device achieved a new all-time best difficulty (unified table)."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT best_difficulty
                FROM device_mining_stats
                WHERE device_id = %s AND best_difficulty > 0
                ORDER BY recorded_at DESC
                LIMIT 1 OFFSET 1
            """, (device_db_id,))

            result = cursor.fetchone()
            previous_best = result[0] if result else 0

            if current_best_diff > 0 and previous_best > 0:
                improvement = ((current_best_diff - previous_best) / previous_best) * 100
                if improvement >= 5:
                    logger.info(f"New best difficulty for {device_id}: {current_best_diff}")
                    self.telegram_notifier.send_best_difficulty_alert(
                        device_id, device_name, current_best_diff, previous_best
                    )
                    self.discord_notifier.send_best_difficulty_alert(
                        device_id, device_name, current_best_diff, previous_best
                    )

        except Exception as e:
            logger.error(f"Error checking best difficulty for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def update_device_status(self, device_id, device_ip, is_online, error_message=""):
        """Update device online/offline status and send notifications if needed."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT is_active, last_seen_at, name
                FROM devices
                WHERE make = %s AND device_id = %s
            """, (self.MAKE, device_id))

            result = cursor.fetchone()
            if not result:
                # Fallback to legacy table for status notifications
                cursor.execute("""
                    SELECT is_active, last_seen_at, device_name
                    FROM bitaxe_devices
                    WHERE device_id = %s
                """, (device_id,))
                result = cursor.fetchone()
                if not result:
                    return

            current_status, last_seen, device_name = result
            self.writer.update_device_status(self.MAKE, device_id, is_online, error_message)

            if current_status and not is_online:
                last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Unknown"
                logger.warning(f"Device {device_id} went offline. Last seen: {last_seen_str}")
                self.telegram_notifier.send_device_offline_alert(
                    device_id, device_name or device_id, last_seen_str, error_message
                )
                self.discord_notifier.send_device_offline_alert(
                    device_id, device_name or device_id, last_seen_str, error_message
                )

            elif not current_status and is_online:
                if last_seen:
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    offline_duration = datetime.now(timezone.utc) - last_seen
                    duration_str = self._format_duration(offline_duration)
                else:
                    duration_str = "Unknown"

                logger.info(f"Device {device_id} came back online after {duration_str}")
                self.telegram_notifier.send_device_online_alert(
                    device_id, device_name or device_id, duration_str
                )
                self.discord_notifier.send_device_online_alert(
                    device_id, device_name or device_id, duration_str
                )

        except Exception as e:
            logger.error(f"Error updating device status for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def _format_duration(self, duration):
        """Format a timedelta object into a human-readable string."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def normalize_system_info(self, system_info: dict, device_id: str) -> NormalizedDeviceSnapshot:
        """Convert raw AxeOS system/info JSON into a NormalizedDeviceSnapshot."""
        hashrate_ghs = float(system_info.get('hashRate', 0) or 0)
        best_difficulty_ever = self._parse_difficulty(system_info.get('bestDiff', '0'))
        best_session_difficulty = self._parse_difficulty(system_info.get('bestSessionDiff', '0'))
        power_watts = float(system_info.get('power', 0) or 0)
        voltage_raw = system_info.get('voltage', 0) or 0
        voltage = float(voltage_raw) / 1000.0  # mV → V

        details = {
            'asic_model': system_info.get('ASICModel'),
            'board_version': system_info.get('boardVersion'),
            'version': system_info.get('version'),
            'axe_os_version': system_info.get('axeOSVersion'),
            'idf_version': system_info.get('idfVersion'),
            'running_partition': system_info.get('runningPartition'),
            'wifi_status': system_info.get('wifiStatus'),
            'core_voltage': system_info.get('coreVoltage'),
            'core_voltage_actual': system_info.get('coreVoltageActual'),
            'pool_difficulty': system_info.get('poolDifficulty'),
            'small_core_count': system_info.get('smallCoreCount'),
            'vr_temp': system_info.get('vrTemp'),
            'temp_target': system_info.get('temptarget'),
            'overheat_mode': system_info.get('overheat_mode', 0),
            'auto_fan_speed': system_info.get('autofanspeed', 1) == 1,
            'fan_speed_percent': system_info.get('fanspeed'),
            'min_fan_speed': system_info.get('minFanSpeed'),
            'max_power': system_info.get('maxPower'),
            'nominal_voltage': system_info.get('nominalVoltage'),
            'overclock_enabled': system_info.get('overclockEnabled', 0) == 1,
            'display_type': system_info.get('display'),
            'display_rotation': system_info.get('rotation', 0),
            'invert_screen': system_info.get('invertscreen', 0) == 1,
            'display_timeout': system_info.get('displayTimeout', -1),
            'stratum_port': system_info.get('stratumPort'),
            'fallback_stratum_port': system_info.get('fallbackStratumPort'),
            'free_heap': system_info.get('freeHeap'),
            'is_psram_available': system_info.get('isPSRAMAvailable', 0) == 1,
        }

        return NormalizedDeviceSnapshot(
            make=self.MAKE,
            device_id=device_id,
            recorded_at=datetime.now(timezone.utc),
            online=True,
            mining=MiningMetrics(
                hashrate_ghs=hashrate_ghs,
                shares_accepted=int(system_info.get('sharesAccepted', 0) or 0),
                shares_rejected=int(system_info.get('sharesRejected', 0) or 0),
                blocks_found=0,
                uptime_seconds=int(system_info.get('uptimeSeconds', 0) or 0),
                best_difficulty=best_difficulty_ever,
                best_session_difficulty=best_session_difficulty,
                pool_url=system_info.get('stratumURL'),
                pool_user=system_info.get('stratumUser'),
            ),
            hardware=HardwareMetrics(
                temperature_c=float(system_info.get('temp', 0) or 0),
                power_watts=power_watts,
                efficiency_j_per_th=efficiency_j_per_th(power_watts, hashrate_ghs),
                fan_speed_rpm=int(system_info.get('fanrpm', 0) or 0),
                fan_speed_percent=system_info.get('fanspeed'),
                voltage=voltage,
                frequency_mhz=float(system_info.get('frequency', 0) or 0),
            ),
            system=SystemMetrics(
                hostname=system_info.get('hostname'),
                mac_address=system_info.get('macAddr'),
                firmware_version=system_info.get('version') or system_info.get('axeOSVersion'),
                model_reported=system_info.get('ASICModel'),
                expected_hashrate_ghs=system_info.get('expectedHashrate'),
                primary_pool_url=system_info.get('stratumURL'),
                primary_pool_user=system_info.get('stratumUser'),
                fallback_pool_url=system_info.get('fallbackStratumURL'),
                using_fallback_pool=system_info.get('isUsingFallbackStratum', 0) == 1,
                wifi_ssid=system_info.get('ssid'),
                wifi_rssi=system_info.get('wifiRSSI'),
                details=details,
            ),
        )

    def collect_device_data(self, device_id, device_ip):
        """Collect mining and hardware data from a single Bitaxe device."""
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
            if not device_row:
                cursor.execute(
                    "SELECT id, device_name FROM bitaxe_devices WHERE device_id = %s",
                    (device_id,),
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
                f"Collected data from device {device_id} - "
                f"Hashrate: {snapshot.mining.hashrate_ghs:.2f} GH/s, "
                f"Temp: {snapshot.hardware.temperature_c}°C, "
                f"Best Ever: {snapshot.mining.best_difficulty}, "
                f"Best Session: {snapshot.mining.best_session_difficulty}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error collecting data from device {device_id} ({device_ip}): {e}", exc_info=True)
            self.update_device_status(device_id, device_ip, False, error_msg)

    def _parse_difficulty(self, diff_str):
        """Parse difficulty string like '22.23 M' to float."""
        import re
        if not diff_str:
            return 0.0

        match = re.match(r'([\d.]+)\s*([KMGT])?', str(diff_str))
        if not match:
            return 0.0

        value = float(match.group(1))
        unit = match.group(2)

        multipliers = {
            'K': 1e3,
            'M': 1e6,
            'G': 1e9,
            'T': 1e12
        }

        return value * multipliers.get(unit, 1)

    def collect_all_devices(self):
        """Collect data from all Bitaxe devices."""
        if not self.devices:
            logger.warning("No Bitaxe devices configured for collection")
            return

        for device in self.devices:
            device_id = device['device_id']
            device_ip = device['ip_address']
            logger.info(f"Collecting data for Bitaxe device: {device_id} at {device_ip}")
            self.collect_device_data(device_id, device_ip)
