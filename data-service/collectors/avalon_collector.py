"""
Avalon Nano 3s device collector
Uses TCP socket-based cgminer API (port 4028) as documented by Canaan.
"""

import json
import logging
import re
import socket
from datetime import datetime

import psycopg2
from notifications.telegram_notifier import TelegramNotifier
from retrying import retry

logger = logging.getLogger(__name__)


class AvalonCollector:
    """Collects data from Avalon Nano 3s mining devices."""

    def __init__(self, database_url):
        self.database_url = database_url
        self.devices = []  # Will be populated from database
        self.telegram_notifier = TelegramNotifier()

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
    def _socket_request(self, ip, command, timeout=10):
        """Make TCP socket request to Avalon device using cgminer API."""
        sock = None
        try:
            # Create socket connection to cgminer API (port 4028)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, 4028))

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
                            mm_id0_content = part[mm_id0_start + 7:]  # Skip "MM ID0="
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
            # Use cgminer ascset command for reboot
            command = "ascset|0,reboot,0"
            logger.info(f"Attempting to restart device {device_id} at {device_ip}:4028")

            response = self._socket_request(device_ip, command)

            if response.get('STATUS') == 'S':  # Success status
                logger.info(f"Successfully sent restart command to device {device_id}")

                # Send notification about the restart
                self.telegram_notifier.send_device_restart_notification(
                    device_id, device_name
                )
                return True
            else:
                logger.warning(f"Restart command may have failed for device {device_id}: {response}")
                return False

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
                FROM avalon_mining_stats
                WHERE device_id = %s
                ORDER BY recorded_at DESC
                LIMIT 3
            """, (device_db_id,))

            recent_hashrates = [row[0] for row in cursor.fetchall()]

            if len(recent_hashrates) >= 3:
                # Check if all 3 values are the same (within 0.01 GH/s tolerance)
                if all(abs(hr - recent_hashrates[0]) < 0.01 for hr in recent_hashrates):
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

    def update_device_status(self, device_id, device_ip, is_online, error_message=""):
        """Update device online/offline status and send notifications if needed."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Get current device status
            cursor.execute("""
                SELECT is_active, last_seen_at, device_name
                FROM avalon_devices
                WHERE device_id = %s
            """, (device_id,))

            result = cursor.fetchone()
            if not result:
                return  # Device doesn't exist yet

            current_status, last_seen, device_name = result

            # Update device status
            cursor.execute("""
                UPDATE avalon_devices
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
                    from datetime import datetime, timezone

                    # Ensure both datetimes are timezone-aware
                    current_time = datetime.now(timezone.utc)
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    offline_duration = current_time - last_seen
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

    def check_best_difficulty_improvement(self, device_db_id, device_id, device_name, current_best_diff):
        """Check if Avalon device achieved a new best difficulty and send notification."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Get the previous best difficulty from the last record
            # For Avalon, best share is stored in the 'difficulty' field
            cursor.execute("""
                SELECT difficulty
                FROM avalon_mining_stats
                WHERE device_id = %s AND difficulty > 0
                ORDER BY recorded_at DESC
                LIMIT 1 OFFSET 1
            """, (device_db_id,))

            result = cursor.fetchone()
            previous_best = result[0] if result else 0

            # Check if current best is significantly higher (at least 5% improvement)
            if current_best_diff > 0 and previous_best > 0:
                improvement = ((current_best_diff - previous_best) / previous_best) * 100
                if improvement >= 5:  # 5% improvement threshold
                    logger.info(f"New best difficulty for Avalon {device_id}: {current_best_diff}")
                    self.telegram_notifier.send_best_difficulty_alert(
                        device_id, device_name, current_best_diff, previous_best
                    )
            elif current_best_diff > 0 and previous_best == 0:
                # First ever best share for this device
                logger.info(f"First best difficulty recorded for Avalon {device_id}: {current_best_diff}")
                self.telegram_notifier.send_best_difficulty_alert(
                    device_id, device_name, current_best_diff, 0
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
        """Parse power consumption from estats response."""
        try:
            # Power information is in MM ID0 field: PS[0 0 27541 4 0 3756 133]
            # The actual power in watts is the LAST value in the PS array
            mm_id0 = stats_info.get('MM ID0', '')

            # Try PS array (last value is power in watts)
            ps_match = re.search(r'PS\[([^\]]+)\]', mm_id0)
            if ps_match:
                ps_values = ps_match.group(1).split()
                if len(ps_values) >= 7:
                    # Power is the last value (index 6) in watts
                    power_watts = float(ps_values[6])
                    return power_watts

            # Fallback: Try MPO field
            mpo_match = re.search(r'MPO\[(\d+)\]', mm_id0)
            if mpo_match:
                return float(mpo_match.group(1))

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

    def collect_device_data(self, device_id, device_ip):
        """Collect mining and hardware data from a single Avalon device."""
        try:
            # Get device information using cgminer API commands
            version_info = self._socket_request(device_ip, 'version')
            summary_info = self._socket_request(device_ip, 'summary')
            stats_info = self._socket_request(device_ip, 'estats')
            pools_info = self._socket_request(device_ip, 'pools')

            # Mark device as online since we got successful responses
            self.update_device_status(device_id, device_ip, True)

            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Get device name from database
            cursor.execute("""
                SELECT id, device_name FROM avalon_devices WHERE device_id = %s
            """, (device_id,))
            device_row = cursor.fetchone()
            device_db_id = device_row[0] if device_row else None
            device_name = device_row[1] if device_row else device_id

            # Use timezone-aware datetime
            from datetime import datetime, timezone
            recorded_at = datetime.now(timezone.utc)

            # Parse mining data from summary
            hashrate_ghs = self._parse_hashrate_mhs(summary_info.get('MHS av', '0'))
            uptime_seconds = int(summary_info.get('Elapsed', 0))
            shares_accepted = int(summary_info.get('Accepted', 0))
            shares_rejected = int(summary_info.get('Rejected', 0))
            blocks_found = int(summary_info.get('Found Blocks', 0))
            best_share = float(summary_info.get('Best Share', 0))

            # Get pool information
            pool_url = pools_info.get('URL') if pools_info else None
            pool_user = pools_info.get('User') if pools_info else None

            # Insert mining stats
            cursor.execute("""
                INSERT INTO avalon_mining_stats (
                    device_id, recorded_at, hashrate_ghs, shares_accepted,
                    shares_rejected, blocks_found, uptime_seconds,
                    difficulty, pool_url, pool_user, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                device_db_id,
                recorded_at,
                hashrate_ghs,
                shares_accepted,
                shares_rejected,
                blocks_found,
                uptime_seconds,
                best_share,
                pool_url,
                pool_user,
                recorded_at
            ))

            # Check for best difficulty improvement and send notifications
            if best_share > 0:
                self.check_best_difficulty_improvement(device_db_id, device_id, device_name, best_share)

            # Parse hardware data from estats
            temperature_c = self._parse_temperature_from_stats(stats_info)
            power_watts = self._parse_power_from_stats(stats_info)
            fan_speed_rpm = self._parse_fan_speed_from_stats(stats_info)
            frequency_mhz = self._parse_frequency_from_stats(stats_info)
            voltage = self._parse_voltage_from_stats(stats_info)

            # Calculate efficiency (J/TH)
            efficiency = (power_watts / (hashrate_ghs / 1000.0)) if hashrate_ghs > 0 else 0

            # Insert hardware logs
            cursor.execute("""
                INSERT INTO avalon_hardware_logs (
                    device_id, recorded_at, power_watts, efficiency_j_per_th,
                    temperature_c, fan_speed_rpm, voltage, frequency_mhz, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                device_db_id,
                recorded_at,
                power_watts,
                efficiency,
                temperature_c,
                fan_speed_rpm,
                voltage,
                frequency_mhz,
                recorded_at
            ))

            # Insert extended system info
            cursor.execute("""
                INSERT INTO avalon_system_info (
                    device_id, recorded_at, device_model, firmware_version, hardware_version,
                    serial_number, mac_address, ip_address, hostname, wifi_ssid, wifi_signal_strength,
                    primary_pool_url, primary_pool_user, backup_pool_url, backup_pool_user, active_pool,
                    system_uptime_seconds, memory_usage_percent, storage_usage_percent,
                    target_frequency, target_voltage, auto_tune_enabled, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
            """, (
                device_db_id, recorded_at,
                version_info.get('MODEL'),
                version_info.get('CGMiner'),
                version_info.get('HWTYPE'),
                version_info.get('DNA'),
                version_info.get('MAC'),
                device_ip,
                device_name,
                None,  # WiFi SSID not available in current API
                None,  # WiFi signal not available
                pool_url,
                pool_user,
                None,  # Backup pool would need additional parsing
                None,  # Backup pool user
                pool_url,  # Active pool (assuming first alive pool)
                uptime_seconds,
                self._parse_memory_usage_from_stats(stats_info),
                0.0,  # Storage usage not available
                frequency_mhz,
                voltage,
                False,  # Auto tune status not directly available
                recorded_at
            ))

            conn.commit()
            cursor.close()
            conn.close()

            # Check for notification conditions after data is saved
            self.check_hashrate_stagnation(device_db_id, device_id, device_name, hashrate_ghs, device_ip)

            logger.info(f"Collected data from device {device_id} - Hashrate: {hashrate_ghs:.2f} GH/s, Temp: {temperature_c}°C")

        except Exception as e:
            # Mark device as offline and log the error
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
            logger.info(f"Collecting data for Avalon device: {device_id} at {device_ip}")
            self.collect_device_data(device_id, device_ip)