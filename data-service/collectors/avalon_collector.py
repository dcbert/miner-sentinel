"""
Avalon Nano 3s device collector
Uses TCP socket-based cgminer API (port 4028) as documented by Canaan.

Normalizes to canonical units and writes via DeviceDataWriter (unified tables only).
"""

import json
import logging
import re
import socket
from datetime import datetime, timezone

import psycopg2
from collectors.normalized import (
    DeviceDataWriter,
    HardwareMetrics,
    MiningMetrics,
    NormalizedDeviceSnapshot,
    SystemMetrics,
    efficiency_j_per_th,
    was_device_online,
)
from notifications.discord_notifier import DiscordNotifier
from notifications.push_notifier import PushNotifier, push_notifier_from_settings
from notifications.emitter import emit_alert, resolve_open_alerts
from notifications.health_checks import run_device_health_checks
from notifications.rules import NotificationRules
from notifications.telegram_notifier import TelegramNotifier
from retrying import retry

logger = logging.getLogger(__name__)


class AvalonCollector:
    """Collects data from Avalon Nano 3s mining devices."""

    MAKE = 'avalon'

    def __init__(self, database_url):
        self.database_url = database_url
        self.devices = []  # Will be populated from database
        self.telegram_notifier = TelegramNotifier()
        self.discord_notifier = DiscordNotifier()
        self.push_notifier = PushNotifier()
        self.notification_rules = NotificationRules()
        self.alert_preferences = {}
        self.writer = DeviceDataWriter(database_url)

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

    def update_push_settings(self, settings: dict):
        """Update ntfy / Gotify / webhook push channels from collector_settings."""
        self.push_notifier = push_notifier_from_settings(settings or {})
        logger.info(f"Push notifier {'enabled' if self.push_notifier.enabled else 'disabled'}")


    def update_notification_rules(self, rules):
        """Update per-event alert toggles and thresholds."""
        self.notification_rules = NotificationRules(rules)
        logger.info(f"Notification rules updated: {self.notification_rules.as_dict()}")

    def update_alert_preferences(self, preferences):
        self.alert_preferences = preferences or {}

    def _notify(self, event_key: str, method_name: str, *args, device_id=None, device_name=None, message=None, payload=None, **kwargs):
        did = device_id if device_id is not None else (args[0] if args else '')
        dname = device_name if device_name is not None else (args[1] if len(args) > 1 else did)
        emit_alert(
            database_url=self.database_url,
            event_key=event_key,
            method_name=method_name,
            telegram=self.telegram_notifier,
            discord=self.discord_notifier,
            push=self.push_notifier,
            rules=self.notification_rules,
            args=args,
            kwargs=kwargs,
            device_make=self.MAKE,
            device_id=str(did) if did is not None else '',
            device_name=str(dname) if dname is not None else '',
            message=message,
            payload=payload,
            preferences=self.alert_preferences,
        )

    def update_devices(self, devices):
        """Update the list of devices to monitor from database."""
        self.devices = devices
        logger.info(f"Updated Avalon device list: {len(devices)} devices")
        for device in devices:
            logger.info(f"  - {device['device_name']} ({device['device_id']}): {device['ip_address']}")

    def get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.database_url)

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _socket_request(self, ip, command, timeout=10, port=4028):
        """Make TCP socket request to Avalon device using cgminer API."""
        sock = None
        try:
            # Create socket connection to cgminer API (default port 4028)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, int(port or 4028)))

            # Send command in JSON format as required by cgminer API
            command_json = json.dumps({"command": command})
            sock.send(command_json.encode('utf-8'))

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

            response_str = response.decode('utf-8', errors='ignore').strip()
            logger.info(f"Socket response from {ip}: {response_str[:200]}...")

            # Parse JSON response directly
            response_str = response_str.replace('\x00', '')

            try:
                parsed = json.loads(response_str)
                # Return the actual data part based on command
                if isinstance(parsed, dict):
                    if command.upper() in parsed and parsed[command.upper()]:
                        return parsed[command.upper()][0] if isinstance(parsed[command.upper()], list) else parsed[command.upper()]
                    elif command.lower() == 'version' and 'VERSION' in parsed and parsed['VERSION']:
                        return parsed['VERSION'][0]
                    elif command.lower() == 'summary' and 'SUMMARY' in parsed and parsed['SUMMARY']:
                        return parsed['SUMMARY'][0]
                    elif command.lower() == 'estats' and 'STATS' in parsed and parsed['STATS']:
                        return parsed['STATS'][0]
                    elif command.lower() == 'pools' and 'POOLS' in parsed and parsed['POOLS']:
                        return parsed['POOLS'][0]  # Return first pool
                    else:
                        # Return full response for debugging
                        return parsed
                return parsed
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response from {ip}: {response_str[:500]}")
                return {"raw_response": response_str}

        except Exception as e:
            logger.error(f"Socket request failed for {ip}: {e}")
            raise
        finally:
            if sock:
                sock.close()

    def _parse_cgminer_response(self, response_str):
        """Parse cgminer API response format."""
        try:
            # cgminer responses are in format: STATUS=...|DATA=...|
            parts = response_str.split('|')
            parsed_data = {}

            for part in parts:
                if '=' in part:
                    # Handle special case for MM ID0 which contains the full hardware stats
                    if part.startswith('STATS=') or 'MM ID0=' in part:
                        # For MM ID0, we need to find the complete field, not split by commas
                        mm_id0_start = part.find('MM ID0=')
                        if mm_id0_start != -1:
                            # Extract everything after MM ID0= until the next field
                            mm_id0_content = part[mm_id0_start + 7 :]  # Skip "MM ID0="
                            # Find where this field ends (look for next major field)
                            for end_marker in [',MM Count=', ',Nonce Mask=', '|']:
                                end_pos = mm_id0_content.find(end_marker)
                                if end_pos != -1:
                                    mm_id0_content = mm_id0_content[:end_pos]
                                    break
                            parsed_data['MM ID0'] = mm_id0_content

                        # Also parse other fields in this part
                        pairs = part.split(',')
                        for pair in pairs:
                            if '=' in pair and not pair.strip().startswith('MM ID0='):
                                key, value = pair.split('=', 1)
                                parsed_data[key.strip()] = value.strip()
                    else:
                        # Normal parsing for other parts
                        if ',' in part:
                            pairs = part.split(',')
                            for pair in pairs:
                                if '=' in pair:
                                    key, value = pair.split('=', 1)
                                    parsed_data[key.strip()] = value.strip()
                        else:
                            # Single key=value pair
                            key, value = part.split('=', 1)
                            parsed_data[key.strip()] = value.strip()

            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing cgminer response: {e}")
            return {}

    def restart_device(self, device_ip, device_id, device_name):
        """Restart an Avalon device via socket API."""
        try:
            # cgminer ascset requires command + parameter fields (not pipe-in-command)
            logger.info(f"Attempting to restart device {device_id} at {device_ip}:4028")
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((device_ip, 4028))
                sock.send(json.dumps({'command': 'ascset', 'parameter': '0,reboot,0'}).encode('utf-8'))
                response = b''
                while True:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        response += data
                    except socket.timeout:
                        break
                raw = response.decode('utf-8', errors='ignore').replace('\x00', '').strip()
                parsed = json.loads(raw) if raw else {}
            finally:
                if sock:
                    sock.close()

            status = parsed.get('STATUS')
            ok = False
            if isinstance(status, list) and status and isinstance(status[0], dict):
                ok = str(status[0].get('STATUS', '')).upper() in ('S', 'SUCCESS')
            elif status == 'S':
                ok = True

            if ok:
                logger.info(f"Successfully sent restart command to device {device_id}")

                # Send notification about the restart
                self._notify(
                    'auto_restart',
                    'send_device_restart_notification',
                    device_id,
                    device_name,
                )
                return True
            else:
                logger.warning(f"Restart command may have failed for device {device_id}: {parsed}")
                return False

        except Exception as e:
            logger.error(f"Failed to restart device {device_id} ({device_ip}): {e}")
            return False

    def check_hashrate_stagnation(self, device_db_id, device_id, device_name, current_hashrate, device_ip):
        """Check if hashrate has been unchanged for N collections (unified table)."""
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
                SELECT hashrate_ghs
                FROM device_mining_stats
                WHERE device_id = %s
                ORDER BY recorded_at DESC
                LIMIT %s
            """,
                (device_db_id, threshold),
            )

            recent_hashrates = [row[0] for row in cursor.fetchall()]

            if len(recent_hashrates) >= threshold:
                if all(abs((hr or 0) - (recent_hashrates[0] or 0)) < tolerance for hr in recent_hashrates):
                    logger.warning(f"Hashrate stagnation detected for {device_id}")
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
                        logger.info(f"Attempting automatic restart for device {device_id} due to hashrate stagnation")
                        self.restart_device(device_ip, device_id, device_name)

        except Exception as e:
            logger.error(f"Error checking hashrate stagnation for {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def update_device_status(self, device_id, device_ip, is_online, error_message=""):
        """Update device online/offline status and send notifications if needed.

        Previous reachability is inferred from error_message + last_seen_at,
        not is_active (which only means the device is enabled for collection).
        """
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

            # Transition: online → offline (only once per outage)
            if previously_online and not is_online:
                last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Unknown"
                logger.warning(f"Device {device_id} went offline. Last seen: {last_seen_str}")
                self._notify(
                    'device_offline',
                    'send_device_offline_alert',
                    device_id,
                    device_name or device_id,
                    last_seen_str,
                    error_message,
                )

            # Transition: offline → online (device had prior contact with an error)
            elif not previously_online and is_online and last_seen is not None:
                current_time = datetime.now(timezone.utc)
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                offline_duration = current_time - last_seen
                duration_str = self._format_duration(offline_duration)

                logger.info(f"Device {device_id} came back online after {duration_str}")
                resolve_open_alerts(self.database_url, 'device_offline', self.MAKE, device_id)
                self._notify(
                    'device_online',
                    'send_device_online_alert',
                    device_id,
                    device_name or device_id,
                    duration_str,
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

    def check_best_difficulty_improvement(self, device_db_id, device_id, device_name, current_best_diff):
        """Check if Avalon device achieved a new best difficulty (unified table)."""
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
                SELECT best_difficulty
                FROM device_mining_stats
                WHERE device_id = %s AND best_difficulty > 0
                ORDER BY recorded_at DESC
                LIMIT 1 OFFSET 1
            """,
                (device_db_id,),
            )

            result = cursor.fetchone()
            previous_best = result[0] if result else 0

            if current_best_diff > 0 and previous_best > 0:
                improvement = ((current_best_diff - previous_best) / previous_best) * 100
                if improvement >= min_improvement:
                    logger.info(f"New best difficulty for Avalon {device_id}: {current_best_diff}")
                    self._notify(
                        'best_difficulty',
                        'send_best_difficulty_alert',
                        device_id,
                        device_name,
                        current_best_diff,
                        previous_best,
                    )
            elif current_best_diff > 0 and previous_best == 0:
                logger.info(f"First best difficulty recorded for Avalon {device_id}: {current_best_diff}")
                self._notify(
                    'best_difficulty',
                    'send_best_difficulty_alert',
                    device_id,
                    device_name,
                    current_best_diff,
                    0,
                )

        except Exception as e:
            logger.error(f"Error checking best difficulty for Avalon {device_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def _parse_hashrate_mhs(self, mhs_str):
        """Parse MHS (Megahashes per second) to GH/s."""
        try:
            mhs_value = float(mhs_str)
            return mhs_value / 1000.0  # Convert MH/s to GH/s
        except (ValueError, TypeError):
            return 0.0

    def _parse_temperature_from_stats(self, stats_info):
        """Parse temperature from estats response."""
        try:
            # Temperature data is in the MM ID0 field
            mm_id0 = stats_info.get('MM ID0', '')

            # Look for OTemp[value] pattern
            otemp_match = re.search(r'OTemp\[(\d+)\]', mm_id0)
            if otemp_match and otemp_match.group(1) != '-273':  # -273 indicates sensor not available
                return float(otemp_match.group(1))

            # Fallback to TAvg[value]
            tavg_match = re.search(r'TAvg\[(\d+)\]', mm_id0)
            if tavg_match:
                return float(tavg_match.group(1))

            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _parse_power_from_stats(self, stats_info):
        """Parse power consumption from estats response.

        GH-16: Nano 3 (non-3s) reports different PS/MPO layout vs 3s.
        Reporter: low=60W, mid=80W, full=100W. Previously saw 326W bogus.
        Prefer MPO (direct watts) when present; fallback to PS last value.
        """
        try:
            mm_id0 = stats_info.get('MM ID0', '')

            # Prefer MPO field (often the reliable direct watts value, especially for Nano 3)
            mpo_match = re.search(r'MPO\[(\d+)\]', mm_id0)
            if mpo_match:
                return float(mpo_match.group(1))

            # Fallback: PS array last value (index 6 in 7-element PS[...])
            ps_match = re.search(r'PS\[([^\]]+)\]', mm_id0)
            if ps_match:
                ps_values = ps_match.group(1).split()
                if len(ps_values) >= 7:
                    power_watts = float(ps_values[6])
                    # Guard against obviously wrong high values for low-power Nano models
                    if power_watts > 300:
                        logger.warning(f"Suspicious high power {power_watts}W from PS for device; check model/firmware")
                    return power_watts

            # Fallback: Try ATA2 array first value
            ata2_match = re.search(r'ATA2\[([^\]]+)\]', mm_id0)
            if ata2_match:
                ata2_values = ata2_match.group(1).split('-')
                if len(ata2_values) >= 1:
                    return float(ata2_values[0])

            return 0.0
        except (ValueError, TypeError, IndexError):
            return 0.0

    def _parse_fan_speed_from_stats(self, stats_info):
        """Parse fan speed from estats response."""
        try:
            # Fan speed is in MM ID0 field: Fan1[1520]
            mm_id0 = stats_info.get('MM ID0', '')
            fan_match = re.search(r'Fan1\[(\d+)\]', mm_id0)

            if fan_match:
                return int(fan_match.group(1))
            return 0
        except (ValueError, TypeError):
            return 0

    def _parse_frequency_from_stats(self, stats_info):
        """Parse frequency from estats response."""
        try:
            # Frequency is in MM ID0 field: Freq[464.89]
            mm_id0 = stats_info.get('MM ID0', '')
            freq_match = re.search(r'Freq\[([\d.]+)\]', mm_id0)

            if freq_match:
                return float(freq_match.group(1))
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _parse_voltage_from_stats(self, stats_info):
        """Parse voltage from estats response."""
        try:
            # Voltage information is in PVT_V0 field: PVT_V0[299 303 301 303 300 301 306 301 297 296 303 305]
            mm_id0 = stats_info.get('MM ID0', '')
            pvt_v0_match = re.search(r'PVT_V0\[([^\]]+)\]', mm_id0)

            if pvt_v0_match:
                # Get first voltage value and convert from centivolts to volts
                voltage_values = pvt_v0_match.group(1).split()
                if voltage_values:
                    voltage_cv = float(voltage_values[0])
                    return voltage_cv / 100.0  # Convert centivolts to volts
            return 0.0
        except (ValueError, TypeError, IndexError):
            return 0.0

    def _parse_memory_usage_from_stats(self, stats_info):
        """Parse memory usage from estats response."""
        try:
            # Memory free is in MM ID0 field: MEMFREE[63728]
            mm_id0 = stats_info.get('MM ID0', '')
            memfree_match = re.search(r'MEMFREE\[(\d+)\]', mm_id0)

            if memfree_match:
                free_kb = float(memfree_match.group(1))
                estimated_total = 128 * 1024  # Assume 128MB total memory
                used_kb = estimated_total - free_kb
                return max(0, (used_kb / estimated_total) * 100.0)
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def normalize_responses(
        self, device_id, device_ip, device_name, version_info, summary_info, stats_info, pools_info
    ) -> NormalizedDeviceSnapshot:
        """Convert cgminer API responses into a NormalizedDeviceSnapshot."""
        hashrate_ghs = self._parse_hashrate_mhs(summary_info.get('MHS 5s', '0'))
        uptime_seconds = int(summary_info.get('Elapsed', 0) or 0)
        shares_accepted = int(summary_info.get('Accepted', 0) or 0)
        shares_rejected = int(summary_info.get('Rejected', 0) or 0)
        blocks_found = int(summary_info.get('Found Blocks', 0) or 0)
        best_share = float(summary_info.get('Best Share', 0) or 0)
        pool_url = pools_info.get('URL') if pools_info else None
        pool_user = pools_info.get('User') if pools_info else None

        temperature_c = self._parse_temperature_from_stats(stats_info)
        power_watts = self._parse_power_from_stats(stats_info)
        fan_speed_rpm = self._parse_fan_speed_from_stats(stats_info)
        frequency_mhz = self._parse_frequency_from_stats(stats_info)
        voltage = self._parse_voltage_from_stats(stats_info)

        details = {
            'hardware_version': version_info.get('HWTYPE') if version_info else None,
            'memory_usage_percent': self._parse_memory_usage_from_stats(stats_info),
            'storage_usage_percent': 0.0,
            'target_frequency': frequency_mhz,
            'target_voltage': voltage,
            'auto_tune_enabled': False,
            'active_pool': pool_url,
            'system_uptime_seconds': uptime_seconds,
            'device_ip': device_ip,
        }

        return NormalizedDeviceSnapshot(
            make=self.MAKE,
            device_id=device_id,
            recorded_at=datetime.now(timezone.utc),
            online=True,
            mining=MiningMetrics(
                hashrate_ghs=hashrate_ghs,
                shares_accepted=shares_accepted,
                shares_rejected=shares_rejected,
                blocks_found=blocks_found,
                uptime_seconds=uptime_seconds,
                best_difficulty=best_share if best_share > 0 else None,
                best_session_difficulty=None,
                pool_url=pool_url,
                pool_user=pool_user,
            ),
            hardware=HardwareMetrics(
                temperature_c=temperature_c,
                power_watts=power_watts,
                efficiency_j_per_th=efficiency_j_per_th(power_watts, hashrate_ghs),
                fan_speed_rpm=fan_speed_rpm,
                voltage=voltage,
                frequency_mhz=frequency_mhz,
            ),
            system=SystemMetrics(
                hostname=device_name,
                mac_address=version_info.get('MAC') if version_info else None,
                firmware_version=version_info.get('CGMiner') if version_info else None,
                serial_number=version_info.get('DNA') if version_info else None,
                model_reported=version_info.get('MODEL') if version_info else None,
                primary_pool_url=pool_url,
                primary_pool_user=pool_user,
                details=details,
            ),
        )

    def collect_device_data(self, device_id, device_ip, port=None):
        """Collect mining and hardware data from a single Avalon device."""
        api_port = int(port or 4028)
        try:
            version_info = self._socket_request(device_ip, 'version', port=api_port)
            summary_info = self._socket_request(device_ip, 'summary', port=api_port)
            stats_info = self._socket_request(device_ip, 'estats', port=api_port)
            pools_info = self._socket_request(device_ip, 'pools', port=api_port)

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

            snapshot = self.normalize_responses(
                device_id, device_ip, device_name,
                version_info, summary_info, stats_info, pools_info,
            )
            device_db_id = self.writer.write_snapshot(snapshot)
            self.update_device_status(device_id, device_ip, True)

            if device_db_id and snapshot.mining:
                if snapshot.mining.best_difficulty and snapshot.mining.best_difficulty > 0:
                    self.check_best_difficulty_improvement(
                        device_db_id, device_id, device_name, snapshot.mining.best_difficulty
                    )
                self.check_hashrate_stagnation(
                    device_db_id, device_id, device_name,
                    snapshot.mining.hashrate_ghs, device_ip,
                )
                run_device_health_checks(
                    database_url=self.database_url,
                    make=self.MAKE,
                    device_db_id=device_db_id,
                    device_id=device_id,
                    device_name=device_name,
                    temperature_c=snapshot.hardware.temperature_c if snapshot.hardware else None,
                    fan_speed_rpm=snapshot.hardware.fan_speed_rpm if snapshot.hardware else None,
                    hashrate_ghs=snapshot.mining.hashrate_ghs,
                    expected_hashrate_ghs=(
                        snapshot.system.expected_hashrate_ghs if snapshot.system else None
                    ),
                    telegram=self.telegram_notifier,
                    discord=self.discord_notifier,
                    push=self.push_notifier,
                    rules=self.notification_rules,
                    preferences=self.alert_preferences,
                )

            logger.info(
                f"Collected data from device {device_id} - "
                f"Hashrate: {snapshot.mining.hashrate_ghs:.2f} GH/s, "
                f"Temp: {snapshot.hardware.temperature_c}°C"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error collecting data from device {device_id} ({device_ip}): {e}", exc_info=True)
            self.update_device_status(device_id, device_ip, False, error_msg)

    def collect_all_devices(self):
        """Collect data from all Avalon devices."""
        if not self.devices:
            logger.warning("No Avalon devices configured for collection")
            return

        for device in self.devices:
            device_id = device['device_id']
            device_ip = device['ip_address']
            port = device.get('port') or 4028
            logger.info(f"Collecting data for Avalon device: {device_id} at {device_ip}:{port}")
            self.collect_device_data(device_id, device_ip, port=port)
