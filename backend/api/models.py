from django.db import models
from django.utils import timezone


class BitAxeDevice(models.Model):
    """BitAxe device registry."""
    device_id = models.CharField(max_length=50, unique=True, db_index=True)
    device_name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(blank=True, null=True, help_text="Last successful connection")
    error_message = models.TextField(blank=True, null=True, help_text="Last error message if offline")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'bitaxe_devices'

    def __str__(self):
        return f"{self.device_name} ({self.device_id})"


class BitAxeMiningStats(models.Model):
    """BitAxe mining statistics."""
    device = models.ForeignKey(BitAxeDevice, on_delete=models.CASCADE, related_name='mining_stats')
    recorded_at = models.DateTimeField(db_index=True)
    hashrate_ghs = models.FloatField(help_text="Hash rate in GH/s")
    shares_accepted = models.IntegerField()
    shares_rejected = models.IntegerField()
    blocks_found = models.IntegerField(default=0)
    uptime_seconds = models.IntegerField()
    best_difficulty = models.BigIntegerField(blank=True, null=True)
    pool_url = models.CharField(max_length=255, blank=True, null=True)
    pool_user = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'bitaxe_mining_stats'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device.device_name}: {self.hashrate_ghs} GH/s at {self.recorded_at}"


class BitAxeHardwareLog(models.Model):
    """BitAxe hardware metrics (power, temperature, etc.)."""
    device = models.ForeignKey(BitAxeDevice, on_delete=models.CASCADE, related_name='hardware_logs')
    recorded_at = models.DateTimeField(db_index=True)
    power_watts = models.FloatField(help_text="Power consumption in Watts")
    efficiency_j_per_th = models.FloatField(blank=True, null=True, help_text="Joules per TeraHash")
    temperature_c = models.FloatField(help_text="Temperature in Celsius")
    fan_speed_rpm = models.IntegerField(blank=True, null=True)
    voltage = models.FloatField(blank=True, null=True)
    frequency_mhz = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'bitaxe_hardware_logs'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device.device_name}: {self.temperature_c}°C, {self.power_watts}W at {self.recorded_at}"


class BitAxeSystemInfo(models.Model):
    """Extended BitAxe system information."""
    device = models.ForeignKey(BitAxeDevice, on_delete=models.CASCADE, related_name='system_info')
    recorded_at = models.DateTimeField(db_index=True)

    # Hardware info
    asic_model = models.CharField(max_length=50, blank=True, null=True)
    board_version = models.CharField(max_length=50, blank=True, null=True)
    hostname = models.CharField(max_length=100, blank=True, null=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)

    # Software versions
    version = models.CharField(max_length=50, blank=True, null=True)
    axe_os_version = models.CharField(max_length=50, blank=True, null=True)
    idf_version = models.CharField(max_length=50, blank=True, null=True)
    running_partition = models.CharField(max_length=50, blank=True, null=True)

    # Network
    ssid = models.CharField(max_length=100, blank=True, null=True)
    wifi_status = models.CharField(max_length=50, blank=True, null=True)
    wifi_rssi = models.IntegerField(blank=True, null=True, help_text="WiFi signal strength")

    # Performance
    core_voltage = models.IntegerField(blank=True, null=True)
    core_voltage_actual = models.IntegerField(blank=True, null=True)
    expected_hashrate = models.FloatField(blank=True, null=True)
    pool_difficulty = models.IntegerField(blank=True, null=True)
    small_core_count = models.IntegerField(blank=True, null=True)

    # Temperature management
    vr_temp = models.IntegerField(blank=True, null=True, help_text="Voltage regulator temperature")
    temp_target = models.IntegerField(blank=True, null=True)
    overheat_mode = models.IntegerField(default=0)

    # Fan control
    auto_fan_speed = models.BooleanField(default=True)
    fan_speed_percent = models.IntegerField(blank=True, null=True)
    min_fan_speed = models.IntegerField(blank=True, null=True)

    # Power settings
    max_power = models.FloatField(blank=True, null=True)
    nominal_voltage = models.FloatField(blank=True, null=True)
    overclock_enabled = models.BooleanField(default=False)

    # Display
    display_type = models.CharField(max_length=50, blank=True, null=True)
    display_rotation = models.IntegerField(default=0)
    invert_screen = models.BooleanField(default=False)
    display_timeout = models.IntegerField(default=-1)

    # Stratum
    stratum_url = models.CharField(max_length=255, blank=True, null=True)
    stratum_port = models.IntegerField(blank=True, null=True)
    stratum_user = models.CharField(max_length=255, blank=True, null=True)
    fallback_stratum_url = models.CharField(max_length=255, blank=True, null=True)
    fallback_stratum_port = models.IntegerField(blank=True, null=True)
    is_using_fallback = models.BooleanField(default=False)

    # Memory
    free_heap = models.BigIntegerField(blank=True, null=True)
    is_psram_available = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'bitaxe_system_info'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device.device_name} System Info at {self.recorded_at}"



class BitAxePoolStats(models.Model):
    """BitAxe mining pool statistics from CKPool."""
    pool_address = models.CharField(max_length=255, db_index=True, help_text="Bitcoin address or pool username")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Hashrate data (stored as strings from API, converted for display)
    hashrate_1m = models.CharField(max_length=20, help_text="1 minute hashrate")
    hashrate_5m = models.CharField(max_length=20, help_text="5 minute hashrate")
    hashrate_1hr = models.CharField(max_length=20, help_text="1 hour hashrate")
    hashrate_1d = models.CharField(max_length=20, help_text="1 day hashrate")
    hashrate_7d = models.CharField(max_length=20, help_text="7 day hashrate")

    # Pool statistics
    lastshare = models.BigIntegerField(help_text="Unix timestamp of last share")
    workers = models.IntegerField(help_text="Number of active workers")
    shares = models.BigIntegerField(help_text="Total shares submitted")
    bestshare = models.FloatField(help_text="Best share difficulty")
    bestever = models.BigIntegerField(help_text="Best ever difficulty")
    authorised = models.BigIntegerField(help_text="Unix timestamp of authorization")

    # Calculated hashrate in GH/s for querying
    hashrate_1m_ghs = models.FloatField(null=True, blank=True, help_text="1m hashrate converted to GH/s")
    hashrate_1d_ghs = models.FloatField(null=True, blank=True, help_text="1d hashrate converted to GH/s")

    class Meta:
        db_table = 'bitaxe_pool_stats'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['pool_address', '-recorded_at']),
            models.Index(fields=['-recorded_at']),
        ]
        verbose_name = "BitAxe Pool Statistics"
        verbose_name_plural = "BitAxe Pool Statistics"

    def __str__(self):
        return f"Pool Stats: {self.hashrate_1m} at {self.recorded_at}"

    def save(self, *args, **kwargs):
        """Convert hashrate strings to GH/s for easier querying."""
        self.hashrate_1m_ghs = self._convert_hashrate_to_ghs(self.hashrate_1m)
        self.hashrate_1d_ghs = self._convert_hashrate_to_ghs(self.hashrate_1d)
        super().save(*args, **kwargs)

    @staticmethod
    def _convert_hashrate_to_ghs(hashrate_str):
        """Convert hashrate string (e.g., '466G', '1.29G', '185M') to GH/s float."""
        if not hashrate_str:
            return 0.0

        # Remove whitespace
        hashrate_str = hashrate_str.strip()

        # Extract number and unit
        import re
        match = re.match(r'([\d.]+)([KMGTP]?)', hashrate_str, re.IGNORECASE)
        if not match:
            return 0.0

        value = float(match.group(1))
        unit = match.group(2).upper()

        # Convert to GH/s
        multipliers = {
            '': 1e-9,      # H/s
            'K': 1e-6,     # KH/s
            'M': 0.001,    # MH/s
            'G': 1,        # GH/s
            'T': 1000,     # TH/s
            'P': 1000000,  # PH/s
        }

        return value * multipliers.get(unit, 1)


# Avalon Nano 3s Models
class AvalonDevice(models.Model):
    """Avalon Nano 3s device registry."""
    device_id = models.CharField(max_length=50, unique=True, db_index=True)
    device_name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'avalon_devices'

    def __str__(self):
        return f"{self.device_name} ({self.device_id})"


class AvalonMiningStats(models.Model):
    """Avalon Nano 3s mining statistics."""
    device = models.ForeignKey(AvalonDevice, on_delete=models.CASCADE, related_name='mining_stats')
    recorded_at = models.DateTimeField(db_index=True)
    hashrate_ghs = models.FloatField(help_text="Hashrate in GH/s")
    shares_accepted = models.IntegerField(default=0)
    shares_rejected = models.IntegerField(default=0)
    blocks_found = models.IntegerField(default=0)
    uptime_seconds = models.IntegerField(default=0)
    difficulty = models.FloatField(default=0.0)
    pool_url = models.CharField(max_length=255, blank=True, null=True)
    pool_user = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'avalon_mining_stats'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device.device_name}: {self.hashrate_ghs} GH/s at {self.recorded_at}"


class AvalonHardwareLogs(models.Model):
    """Avalon Nano 3s hardware monitoring data."""
    device = models.ForeignKey(AvalonDevice, on_delete=models.CASCADE, related_name='hardware_logs')
    recorded_at = models.DateTimeField(db_index=True)
    power_watts = models.FloatField(default=0.0)
    efficiency_j_per_th = models.FloatField(default=0.0, help_text="Power efficiency in J/TH")
    temperature_c = models.FloatField(default=0.0)
    fan_speed_rpm = models.IntegerField(default=0)
    voltage = models.FloatField(default=0.0)
    frequency_mhz = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'avalon_hardware_logs'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device.device_name}: {self.temperature_c}°C, {self.power_watts}W at {self.recorded_at}"


class AvalonSystemInfo(models.Model):
    """Avalon Nano 3s extended system information."""
    device = models.ForeignKey(AvalonDevice, on_delete=models.CASCADE, related_name='system_info')
    recorded_at = models.DateTimeField(db_index=True)

    # Device info
    device_model = models.CharField(max_length=100, blank=True, null=True)
    firmware_version = models.CharField(max_length=100, blank=True, null=True)
    hardware_version = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    mac_address = models.CharField(max_length=18, blank=True, null=True)

    # Network info
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    wifi_ssid = models.CharField(max_length=255, blank=True, null=True)
    wifi_signal_strength = models.IntegerField(blank=True, null=True)

    # Pool configuration
    primary_pool_url = models.CharField(max_length=255, blank=True, null=True)
    primary_pool_user = models.CharField(max_length=255, blank=True, null=True)
    backup_pool_url = models.CharField(max_length=255, blank=True, null=True)
    backup_pool_user = models.CharField(max_length=255, blank=True, null=True)
    active_pool = models.CharField(max_length=255, blank=True, null=True)

    # System status
    system_uptime_seconds = models.IntegerField(default=0)
    memory_usage_percent = models.FloatField(default=0.0)
    storage_usage_percent = models.FloatField(default=0.0)

    # Mining configuration
    target_frequency = models.FloatField(default=0.0)
    target_voltage = models.FloatField(default=0.0)
    auto_tune_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'avalon_system_info'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device.device_name} System Info at {self.recorded_at}"


class CollectorSettings(models.Model):
    """
    Singleton model for data collector configuration.
    Stores settings that were previously in environment variables.
    """
    # Pool type choices
    POOL_TYPE_CHOICES = [
        ('ckpool', 'CKPool'),
        ('publicpool', 'Public Pool'),
    ]

    # Polling configuration
    polling_interval_minutes = models.IntegerField(
        default=15,
        help_text="How often to poll devices for data (in minutes)"
    )
    device_check_interval_minutes = models.IntegerField(
        default=5,
        help_text="How often to check for new/updated devices (in minutes)"
    )

    # Pool type selection
    pool_type = models.CharField(
        max_length=20,
        choices=POOL_TYPE_CHOICES,
        default='ckpool',
        help_text="Select which mining pool to use for statistics"
    )

    # CKPool configuration
    ckpool_address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Bitcoin address for CKPool statistics"
    )
    ckpool_url = models.CharField(
        max_length=255,
        default='https://eusolo.ckpool.org',
        help_text="CKPool server URL"
    )

    # PublicPool configuration
    publicpool_address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Bitcoin address for PublicPool statistics"
    )
    publicpool_url = models.CharField(
        max_length=255,
        blank=True,
        default='http://localhost:3334',
        help_text="PublicPool API URL (e.g., http://localhost:3334 or https://web.public-pool.io)"
    )

    # Telegram notifications (optional)
    telegram_enabled = models.BooleanField(default=False)
    telegram_bot_token = models.CharField(max_length=255, blank=True, default='')
    telegram_chat_id = models.CharField(max_length=255, blank=True, default='')

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'collector_settings'
        verbose_name = 'Collector Settings'
        verbose_name_plural = 'Collector Settings'

    def __str__(self):
        return f"Collector Settings (updated: {self.updated_at})"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of settings - do nothing."""
        return (0, {})  # Return empty deletion result

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
