"""
Bitaxe device collector
"""

import logging
from datetime import datetime

import psycopg2
import requests
from notifications.telegram_notifier import TelegramNotifier
from retrying import retry

logger = logging.getLogger(__name__)


class BitAxeCollector:
    """Collects data from Bitaxe mining devices."""

    def __init__(self, database_url):
        self.database_url = database_url
        self.devices = []  # Will be populated from database
        self.telegram_notifier = TelegramNotifier()

    def update_telegram_settings(self, enabled, bot_token, chat_id):
        """Update telegram notification settings."""
        logger.info(f"Updating telegram settings: enabled={enabled}")
        if enabled and bot_token and chat_id:
            self.telegram_notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
            logger.info("Telegram notifier enabled with settings from database")
        else:
            self.telegram_notifier = TelegramNotifier()  # Disabled
            logger.info("Telegram notifier disabled")

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

            return True

        except Exception as e:
            logger.error(f"Failed to restart device {device_id} ({device_ip}): {e}")
            return False

    def check_hashrate_stagnation(self, device_db_id, device_id, device_name, current_hashrate, device_ip):
        """Check if hashrate has been unchanged for 3 collections."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Get last 3 hashrate values
            cursor.execute("""
                SELECT hashrate_ghs
                FROM bitaxe_mining_stats
                WHERE device_id = %s
                ORDER BY recorded_at DESC
                LIMIT 3
            """, (device_db_id,))

            recent_hashrates = [row[0] for row in cursor.fetchall()]

            if len(recent_hashrates) >= 3:
                # Check if all 3 values are the same (within 0.1 GH/s tolerance)
                if all(abs(hr - recent_hashrates[0]) < 0.1 for hr in recent_hashrates):
                    logger.warning(f"Hashrate stagnation detected for {device_id}")

                    # Send alert notification
                    self.telegram_notifier.send_hashrate_alert(
                        device_id, device_name, current_hashrate, 3
                    )

                    # Attempt automatic restart
                    logger.info(f"Attempting automatic restart for device {device_id} due to hashrate stagnation")
                    self.restart_device(device_ip, device_id, device_name)

        except Exception as e:
            logger.error(f"Error checking hashrate stagnation for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def check_best_difficulty_improvement(self, device_db_id, device_id, device_name, current_best_diff):
        """Check if device achieved a new all-time best difficulty.

        Args:
            device_db_id: Database ID of the device
            device_id: Human-readable device identifier
            device_name: Display name of the device
            current_best_diff: Current all-time best difficulty (from API 'bestDiff' field)
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Get the previous all-time best difficulty from the last record
            # We compare best_difficulty (all-time) values, not session values
            cursor.execute("""
                SELECT best_difficulty
                FROM bitaxe_mining_stats
                WHERE device_id = %s AND best_difficulty > 0
                ORDER BY recorded_at DESC
                LIMIT 1 OFFSET 1
            """, (device_db_id,))

            result = cursor.fetchone()
            previous_best = result[0] if result else 0

            # Check if current best is significantly higher (at least 5% improvement)
            if current_best_diff > 0 and previous_best > 0:
                improvement = ((current_best_diff - previous_best) / previous_best) * 100
                if improvement >= 5:  # 5% improvement threshold
                    logger.info(f"New best difficulty for {device_id}: {current_best_diff}")
                    self.telegram_notifier.send_best_difficulty_alert(
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
            # Get current device status
            cursor.execute("""
                SELECT is_active, last_seen_at, device_name
                FROM bitaxe_devices
                WHERE device_id = %s
            """, (device_id,))

            result = cursor.fetchone()
            if not result:
                return  # Device doesn't exist yet

            current_status, last_seen, device_name = result

            # Update device status
            cursor.execute("""
                UPDATE bitaxe_devices
                SET last_seen_at = CASE WHEN %s THEN NOW() ELSE last_seen_at END,
                    error_message = %s
                WHERE device_id = %s
            """, (is_online, error_message, device_id))

            conn.commit()

            # Check if status changed and send notifications
            if current_status and not is_online:
                # Device went offline
                last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Unknown"
                logger.warning(f"Device {device_id} went offline. Last seen: {last_seen_str}")
                self.telegram_notifier.send_device_offline_alert(
                    device_id, device_name or device_id, last_seen_str, error_message
                )

            elif not current_status and is_online:
                # Device came back online
                if last_seen:
                    from datetime import datetime
                    offline_duration = datetime.utcnow() - last_seen
                    duration_str = self._format_duration(offline_duration)
                else:
                    duration_str = "Unknown"

                logger.info(f"Device {device_id} came back online after {duration_str}")
                self.telegram_notifier.send_device_online_alert(
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

    def collect_device_data(self, device_id, device_ip):
        """Collect mining and hardware data from a single Bitaxe device."""
        try:
            # Fetch data from Bitaxe API
            system_info = self._api_request(device_ip, 'api/system/info')

            # Mark device as online since we got a successful response
            self.update_device_status(device_id, device_ip, True)

            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Get device name from database
            cursor.execute("""
                SELECT id, device_name FROM bitaxe_devices WHERE device_id = %s
            """, (device_id,))
            device_row = cursor.fetchone()
            device_db_id = device_row[0] if device_row else None
            device_name = device_row[1] if device_row else device_id

            recorded_at = datetime.utcnow()

            # Parse hashrate (already in GH/s from API)
            hashrate_ghs = system_info.get('hashRate', 0)

            # Parse best difficulties from API:
            # - bestDiff: All-time best difficulty ever achieved by device
            # - bestSessionDiff: Best difficulty achieved in current mining session
            best_diff_str = system_info.get('bestDiff', '0')
            best_difficulty_ever = self._parse_difficulty(best_diff_str)

            best_session_str = system_info.get('bestSessionDiff', '0')
            best_session_difficulty = self._parse_difficulty(best_session_str)

            # Insert mining stats
            cursor.execute("""
                INSERT INTO bitaxe_mining_stats (
                    device_id, recorded_at, hashrate_ghs, shares_accepted,
                    shares_rejected, blocks_found, uptime_seconds,
                    best_difficulty, best_session_difficulty, pool_url, pool_user
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                device_db_id,
                recorded_at,
                hashrate_ghs,
                system_info.get('sharesAccepted', 0),
                system_info.get('sharesRejected', 0),
                0,  # blocks_found not in API
                system_info.get('uptimeSeconds', 0),
                best_difficulty_ever,      # best_difficulty = all-time best (from 'bestDiff')
                best_session_difficulty,   # best_session_difficulty = session best (from 'bestSessionDiff')
                system_info.get('stratumURL'),
                system_info.get('stratumUser')
            ))

            # Calculate efficiency (J/TH)
            # Efficiency = Power (W) / Hashrate (TH/s)
            efficiency = (system_info.get('power', 0) / (hashrate_ghs / 1000.0)) if hashrate_ghs > 0 else 0

            # Insert hardware logs
            cursor.execute("""
                INSERT INTO bitaxe_hardware_logs (
                    device_id, recorded_at, power_watts, efficiency_j_per_th,
                    temperature_c, fan_speed_rpm, voltage, frequency_mhz
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                device_db_id,
                recorded_at,
                system_info.get('power', 0),
                efficiency,
                system_info.get('temp', 0),
                system_info.get('fanrpm', 0),
                system_info.get('voltage', 0) / 1000.0,  # Convert mV to V
                system_info.get('frequency', 0)
            ))

            # Insert extended system info
            cursor.execute("""
                INSERT INTO bitaxe_system_info (
                    device_id, recorded_at, asic_model, board_version, hostname, mac_address,
                    version, axe_os_version, idf_version, running_partition,
                    ssid, wifi_status, wifi_rssi,
                    core_voltage, core_voltage_actual, expected_hashrate, pool_difficulty, small_core_count,
                    vr_temp, temp_target, overheat_mode,
                    auto_fan_speed, fan_speed_percent, min_fan_speed,
                    max_power, nominal_voltage, overclock_enabled,
                    display_type, display_rotation, invert_screen, display_timeout,
                    stratum_url, stratum_port, stratum_user, fallback_stratum_url, fallback_stratum_port, is_using_fallback,
                    free_heap, is_psram_available
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                device_db_id, recorded_at,
                system_info.get('ASICModel'), system_info.get('boardVersion'),
                system_info.get('hostname'), system_info.get('macAddr'),
                system_info.get('version'), system_info.get('axeOSVersion'),
                system_info.get('idfVersion'), system_info.get('runningPartition'),
                system_info.get('ssid'), system_info.get('wifiStatus'), system_info.get('wifiRSSI'),
                system_info.get('coreVoltage'), system_info.get('coreVoltageActual'),
                system_info.get('expectedHashrate'), system_info.get('poolDifficulty'),
                system_info.get('smallCoreCount'),
                system_info.get('vrTemp'), system_info.get('temptarget'), system_info.get('overheat_mode'),
                system_info.get('autofanspeed', 1) == 1, system_info.get('fanspeed'), system_info.get('minFanSpeed'),
                system_info.get('maxPower'), system_info.get('nominalVoltage'), system_info.get('overclockEnabled', 0) == 1,
                system_info.get('display'), system_info.get('rotation'), system_info.get('invertscreen', 0) == 1,
                system_info.get('displayTimeout'),
                system_info.get('stratumURL'), system_info.get('stratumPort'), system_info.get('stratumUser'),
                system_info.get('fallbackStratumURL'), system_info.get('fallbackStratumPort'),
                system_info.get('isUsingFallbackStratum', 0) == 1,
                system_info.get('freeHeap'), system_info.get('isPSRAMAvailable', 0) == 1
            ))

            conn.commit()
            cursor.close()
            conn.close()

            # Check for notification conditions after data is saved
            self.check_hashrate_stagnation(device_db_id, device_id, device_name, hashrate_ghs, device_ip)
            # Use all-time best difficulty for improvement notifications (more meaningful achievement)
            self.check_best_difficulty_improvement(device_db_id, device_id, device_name, best_difficulty_ever)

            logger.info(
                f"Collected data from device {device_id} - "
                f"Hashrate: {hashrate_ghs:.2f} GH/s, "
                f"Temp: {system_info.get('temp')}°C, "
                f"Best Ever: {best_difficulty_ever}, "
                f"Best Session: {best_session_difficulty}"
            )

        except Exception as e:
            # Mark device as offline and log the error
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
