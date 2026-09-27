from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Unified multi-make device + pool models
# ---------------------------------------------------------------------------

class Device(models.Model):
    """Unified device registry for all miner makes."""

    MAKE_BITAXE = 'bitaxe'
    MAKE_AVALON = 'avalon'
    MAKE_NMAXE = 'nmaxe'  # NMAxe / NMAxeGamma (NMTech fork, nested AxeOS-style API)
    MAKE_NERDNOS = 'nerdnos'  # NerdNOS (Metal Edition) — separate HTTP /api/status
    MAKE_ANTMINER = 'antminer'
    MAKE_WHATSMINER = 'whatsminer'
    MAKE_BRAIINS = 'braiins'
    MAKE_GOLDSHELL = 'goldshell'
    MAKE_ICERIVER = 'iceriver'
    MAKE_OTHER = 'other'
    MAKE_CHOICES = [
        (MAKE_BITAXE, 'Bitaxe'),
        (MAKE_AVALON, 'Avalon'),
        (MAKE_NMAXE, 'NMAxe'),
        (MAKE_NERDNOS, 'NerdNOS'),
        (MAKE_ANTMINER, 'Antminer'),
        (MAKE_WHATSMINER, 'Whatsminer'),
        (MAKE_BRAIINS, 'Braiins'),
        (MAKE_GOLDSHELL, 'Goldshell'),
        (MAKE_ICERIVER, 'IceRiver'),
        (MAKE_OTHER, 'Other'),
    ]

    PROTOCOL_HTTP_AXEOS = 'http_axeos'
    PROTOCOL_CGMINER_TCP = 'cgminer_tcp'
    PROTOCOL_HTTP_NMAXE = 'http_nmaxe'
    PROTOCOL_HTTP_NERDNOS = 'http_nerdnos'
    PROTOCOL_WHATSMINER_API = 'whatsminer_api'
    PROTOCOL_BRAIINS = 'braiins'
    PROTOCOL_CUSTOM = 'custom'
    PROTOCOL_CHOICES = [
        (PROTOCOL_HTTP_AXEOS, 'HTTP AxeOS'),
        (PROTOCOL_CGMINER_TCP, 'cgminer TCP'),
        (PROTOCOL_HTTP_NMAXE, 'HTTP NMAxe'),
        (PROTOCOL_HTTP_NERDNOS, 'HTTP NerdNOS'),
        (PROTOCOL_WHATSMINER_API, 'Whatsminer API'),
        (PROTOCOL_BRAIINS, 'Braiins'),
        (PROTOCOL_CUSTOM, 'Custom'),
    ]

    device_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=100)
    make = models.CharField(max_length=32, choices=MAKE_CHOICES, db_index=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    protocol = models.CharField(max_length=32, choices=PROTOCOL_CHOICES)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    connection_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'devices'
        unique_together = [('make', 'device_id')]
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['make']),
            models.Index(fields=['last_seen_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.make}:{self.device_id})"


class DeviceMiningStats(models.Model):
    """Normalized mining statistics for any device make."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mining_stats')
    recorded_at = models.DateTimeField(db_index=True)
    hashrate_ghs = models.FloatField(default=0.0, help_text="Hashrate in GH/s (canonical)")
    hashrate_avg_ghs = models.FloatField(blank=True, null=True)
    shares_accepted = models.BigIntegerField(default=0)
    shares_rejected = models.BigIntegerField(default=0)
    hardware_errors = models.BigIntegerField(blank=True, null=True)
    blocks_found = models.IntegerField(default=0)
    uptime_seconds = models.IntegerField(default=0)
    best_difficulty = models.FloatField(blank=True, null=True, help_text="All-time best share difficulty")
    best_session_difficulty = models.FloatField(blank=True, null=True)
    pool_url = models.CharField(max_length=255, blank=True, null=True)
    pool_user = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'device_mining_stats'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
            models.Index(fields=['-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device}: {self.hashrate_ghs} GH/s at {self.recorded_at}"


class DeviceHardwareStats(models.Model):
    """Normalized hardware metrics for any device make."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='hardware_stats')
    recorded_at = models.DateTimeField(db_index=True)
    temperature_c = models.FloatField(blank=True, null=True, help_text="Primary temperature °C")
    temperature_board_c = models.FloatField(blank=True, null=True)
    temperature_chip_c = models.FloatField(blank=True, null=True)
    power_watts = models.FloatField(blank=True, null=True)
    efficiency_j_per_th = models.FloatField(blank=True, null=True)
    fan_speed_rpm = models.IntegerField(blank=True, null=True)
    fan_speed_percent = models.IntegerField(blank=True, null=True)
    voltage = models.FloatField(blank=True, null=True, help_text="Volts")
    frequency_mhz = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'device_hardware_stats'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
            models.Index(fields=['-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device}: {self.temperature_c}°C, {self.power_watts}W at {self.recorded_at}"


class DeviceSystemInfo(models.Model):
    """Normalized system/inventory snapshot; vendor extras in details JSON."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='system_info')
    recorded_at = models.DateTimeField(db_index=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    mac_address = models.CharField(max_length=32, blank=True, null=True)
    firmware_version = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    model_reported = models.CharField(max_length=100, blank=True, null=True)
    expected_hashrate_ghs = models.FloatField(blank=True, null=True)
    primary_pool_url = models.CharField(max_length=255, blank=True, null=True)
    primary_pool_user = models.CharField(max_length=255, blank=True, null=True)
    fallback_pool_url = models.CharField(max_length=255, blank=True, null=True)
    fallback_pool_user = models.CharField(max_length=255, blank=True, null=True)
    using_fallback_pool = models.BooleanField(blank=True, null=True)
    wifi_ssid = models.CharField(max_length=255, blank=True, null=True)
    wifi_rssi = models.IntegerField(blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'device_system_info'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.device} System Info at {self.recorded_at}"


class AlertEvent(models.Model):
    """
    Persisted activity / alert journal (control audits + collector alerts).

    Shared by collectors (chat + Activity) and control actions (audit rows).
    """

    SEVERITY_INFO = 'info'
    SEVERITY_WARN = 'warn'
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARN, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    event_type = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(
        max_length=16,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
        db_index=True,
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alert_events',
    )
    device_make = models.CharField(max_length=32, blank=True, default='')
    device_key = models.CharField(
        max_length=64, blank=True, default='',
        help_text='Vendor device_id string',
    )
    device_name = models.CharField(max_length=100, blank=True, default='')
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(
        max_length=191,
        blank=True,
        default='',
        db_index=True,
        help_text='Dedup key: event_type + device identity',
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    muted_until = models.DateTimeField(blank=True, null=True)
    last_notified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'alert_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['device', '-created_at']),
            models.Index(fields=['fingerprint', '-created_at']),
            models.Index(fields=['resolved_at', 'acknowledged_at']),
            models.Index(fields=['severity', '-created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} [{self.severity}] at {self.created_at}"

    @property
    def is_open(self):
        return self.resolved_at is None and self.acknowledged_at is None

    @property
    def is_muted(self):
        if not self.muted_until:
            return False
        return self.muted_until > timezone.now()


class PoolStats(models.Model):
    """Normalized mining pool statistics (CKPool, PublicPool, future sources)."""


    POOL_CKPOOL = 'ckpool'
    POOL_PUBLICPOOL = 'publicpool'
    POOL_BTCPOWLAB = 'btcpowlab'
    POOL_PARASITE = 'parasite'
    POOL_OCEAN = 'ocean'
    POOL_OTHER = 'other'
    POOL_TYPE_CHOICES = [
        (POOL_CKPOOL, 'CKPool'),
        (POOL_PUBLICPOOL, 'Public Pool'),
        (POOL_BTCPOWLAB, 'BTC PoW Lab'),
        (POOL_PARASITE, 'Parasite'),
        (POOL_OCEAN, 'Ocean'),
        (POOL_OTHER, 'Other'),
    ]

    pool_type = models.CharField(max_length=32, choices=POOL_TYPE_CHOICES, db_index=True)
    pool_address = models.CharField(max_length=255, db_index=True)
    pool_url = models.CharField(max_length=255, blank=True, null=True)
    recorded_at = models.DateTimeField(db_index=True)

    hashrate_1m_ghs = models.FloatField(blank=True, null=True)
    hashrate_5m_ghs = models.FloatField(blank=True, null=True)
    hashrate_1h_ghs = models.FloatField(blank=True, null=True)
    hashrate_1d_ghs = models.FloatField(blank=True, null=True)
    hashrate_7d_ghs = models.FloatField(blank=True, null=True)

    hashrate_1m_display = models.CharField(max_length=32, blank=True, null=True)
    hashrate_5m_display = models.CharField(max_length=32, blank=True, null=True)
    hashrate_1h_display = models.CharField(max_length=32, blank=True, null=True)
    hashrate_1d_display = models.CharField(max_length=32, blank=True, null=True)
    hashrate_7d_display = models.CharField(max_length=32, blank=True, null=True)

    workers = models.IntegerField(blank=True, null=True)
    shares = models.BigIntegerField(blank=True, null=True)
    best_share = models.FloatField(blank=True, null=True)
    best_ever = models.FloatField(blank=True, null=True)
    last_share_at = models.DateTimeField(blank=True, null=True)
    last_share_unix = models.BigIntegerField(blank=True, null=True)
    authorised_unix = models.BigIntegerField(blank=True, null=True)

    pool_total_miners = models.IntegerField(blank=True, null=True)
    pool_total_hashrate_ghs = models.FloatField(blank=True, null=True)

    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'pool_stats'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['pool_type', 'pool_address', '-recorded_at']),
            models.Index(fields=['-recorded_at']),
            models.Index(fields=['pool_type', '-recorded_at']),
        ]
        verbose_name = 'Pool Statistics'
        verbose_name_plural = 'Pool Statistics'

    def __str__(self):
        return f"{self.pool_type}:{self.pool_address} {self.hashrate_1m_ghs} GH/s at {self.recorded_at}"


# Default per-event notification rules (user can toggle/tune via Settings → Notifications)
DEFAULT_NOTIFICATION_RULES = {
    'device_offline': {
        'enabled': True,
        'label': 'Device offline',
        'description': 'Alert when a device becomes unreachable',
        'severity': 'critical',
    },
    'device_online': {
        'enabled': True,
        'label': 'Device back online',
        'description': 'Alert when a previously offline device recovers',
        'severity': 'info',
    },
    'hashrate_stagnation': {
        'enabled': True,
        'label': 'Hashrate stagnation',
        'description': 'Alert when hashrate stays flat across multiple polls',
        'threshold_collections': 3,
        'tolerance_ghs': 0.1,
        'severity': 'warn',
    },
    'auto_restart': {
        'enabled': True,
        'label': 'Auto-restart on stagnation',
        'description': 'Attempt remote restart when hashrate stagnation is detected',
        'severity': 'warn',
    },
    'best_difficulty': {
        'enabled': True,
        'label': 'New best difficulty',
        'description': 'Celebrate personal best share difficulty improvements',
        'min_improvement_percent': 5.0,
        'severity': 'info',
    },
    'temperature_high': {
        'enabled': True,
        'label': 'High temperature',
        'description': 'Alert when device temperature stays above threshold across polls',
        'threshold_c': 80.0,
        'duration_polls': 2,
        'severity': 'critical',
    },
    'fan_dead': {
        'enabled': True,
        'label': 'Fan not spinning',
        'description': 'Alert when fan RPM is ~0 while the device is hashing',
        'severity': 'critical',
    },
    'pool_down': {
        'enabled': True,
        'label': 'Pool stats unavailable',
        'description': 'Alert when pool API fails or no fresh pool stats arrive',
        'stale_minutes': 30,
        'severity': 'warn',
    },
    'collector_down': {
        'enabled': True,
        'label': 'Collector unhealthy',
        'description': 'Alert when the data collector fails or stops reporting',
        'severity': 'critical',
    },
    'expected_hashrate_drop': {
        'enabled': True,
        'label': 'Hashrate below expected',
        'description': 'Alert when live hashrate falls below expected by a configured percent',
        'drop_percent': 30.0,
        'severity': 'warn',
    },
}

_SEVERITY_CHOICES = {'info', 'warn', 'critical'}


def merge_notification_rules(raw):
    """Deep-merge stored rules with defaults (unknown keys ignored)."""
    merged = {}
    stored = raw if isinstance(raw, dict) else {}
    for key, defaults in DEFAULT_NOTIFICATION_RULES.items():
        entry = dict(defaults)
        user = stored.get(key)
        if isinstance(user, dict):
            if 'enabled' in user:
                entry['enabled'] = bool(user['enabled'])
            if 'severity' in user and user['severity'] in _SEVERITY_CHOICES:
                entry['severity'] = user['severity']
            if key == 'hashrate_stagnation':
                try:
                    n = int(user.get('threshold_collections', entry['threshold_collections']))
                    entry['threshold_collections'] = max(2, min(20, n))
                except (TypeError, ValueError):
                    pass
                try:
                    t = float(user.get('tolerance_ghs', entry['tolerance_ghs']))
                    entry['tolerance_ghs'] = max(0.0, min(100.0, t))
                except (TypeError, ValueError):
                    pass
            if key == 'best_difficulty':
                try:
                    p = float(user.get('min_improvement_percent', entry['min_improvement_percent']))
                    entry['min_improvement_percent'] = max(0.0, min(100.0, p))
                except (TypeError, ValueError):
                    pass
            if key == 'temperature_high':
                try:
                    t = float(user.get('threshold_c', entry['threshold_c']))
                    entry['threshold_c'] = max(40.0, min(120.0, t))
                except (TypeError, ValueError):
                    pass
                try:
                    n = int(user.get('duration_polls', entry['duration_polls']))
                    entry['duration_polls'] = max(1, min(20, n))
                except (TypeError, ValueError):
                    pass
            if key == 'pool_down':
                try:
                    n = int(user.get('stale_minutes', entry['stale_minutes']))
                    entry['stale_minutes'] = max(5, min(1440, n))
                except (TypeError, ValueError):
                    pass
            if key == 'expected_hashrate_drop':
                try:
                    p = float(user.get('drop_percent', entry['drop_percent']))
                    entry['drop_percent'] = max(5.0, min(95.0, p))
                except (TypeError, ValueError):
                    pass
        merged[key] = entry
    return merged


class CollectorSettings(models.Model):
    """
    Singleton model for data collector configuration.
    Stores settings that were previously in environment variables.
    """
    # Pool type choices
    POOL_TYPE_CHOICES = [
        ('ckpool', 'CKPool'),
        ('publicpool', 'Public Pool'),
        ('btcpowlab', 'BTC PoW Lab'),
        ('parasite', 'Parasite'),
    ]

    # Polling configuration (home fleets: ~1–2 min default)
    polling_interval_minutes = models.IntegerField(
        default=2,
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

    # BTC PoW Lab configuration
    btcpowlab_address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Bitcoin address for BTC PoW Lab statistics"
    )
    btcpowlab_url = models.CharField(
        max_length=255,
        blank=True,
        default='https://btcpowlab-pool.com/public/v1',
        help_text="BTC PoW Lab public API base URL"
    )

    # Parasite Pool configuration
    parasite_address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Bitcoin address for Parasite Pool statistics"
    )
    parasite_url = models.CharField(
        max_length=255,
        blank=True,
        default='https://parasite.space/api',
        help_text="Parasite Pool public API base URL"
    )

    # Telegram notifications (optional)
    telegram_enabled = models.BooleanField(default=False)
    telegram_bot_token = models.CharField(max_length=255, blank=True, default='')
    telegram_chat_id = models.CharField(max_length=255, blank=True, default='')

    # Discord webhook notifications (optional)
    discord_enabled = models.BooleanField(default=False)
    discord_webhook_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Discord webhook URL for alerts (create in Discord channel settings)"
    )

    # ntfy / Gotify / generic webhook (Umbrel-friendly push channels)
    ntfy_enabled = models.BooleanField(
        default=False,
        help_text="Enable ntfy push notifications (topic URL)",
    )
    ntfy_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Full ntfy topic URL (e.g. https://ntfy.sh/mytopic or self-hosted)",
    )
    ntfy_token = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Optional ntfy access token",
    )
    gotify_enabled = models.BooleanField(
        default=False,
        help_text="Enable Gotify push notifications",
    )
    gotify_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Gotify server base URL (e.g. https://gotify.example.com)",
    )
    gotify_token = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Gotify application token",
    )
    webhook_enabled = models.BooleanField(
        default=False,
        help_text="Enable generic JSON webhook for alerts",
    )
    webhook_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="POST JSON alerts to this URL",
    )

    # Per-event notification rules (enable/disable + thresholds). See DEFAULT_NOTIFICATION_RULES.
    notification_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Alert type toggles and tuning (offline, online, stagnation, restart, best difficulty)",
    )

    # Quiet hours + re-alert cadence (non-critical suppressed during quiet window)
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text="When enabled, info/warn alerts skip chat during quiet hours (critical still delivered)",
    )
    quiet_hours_start = models.CharField(
        max_length=5,
        default='22:00',
        help_text="Quiet hours start (HH:MM, local server time)",
    )
    quiet_hours_end = models.CharField(
        max_length=5,
        default='07:00',
        help_text="Quiet hours end (HH:MM, local server time)",
    )
    alert_repeat_minutes = models.IntegerField(
        default=60,
        help_text="Minutes before re-notifying the same open problem via chat",
    )

    # Retention (0 = keep forever for that category)
    metrics_retention_days = models.IntegerField(
        default=90,
        help_text="Days to keep device_*_stats and pool_stats (0 = forever)",
    )
    alert_retention_days = models.IntegerField(
        default=0,
        help_text="Days to keep resolved AlertEvents (0 = forever; open alerts never pruned)",
    )

    # Cost Analysis Settings
    energy_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.12,
        help_text="Energy cost per kWh in selected currency"
    )
    energy_currency = models.CharField(
        max_length=3,
        choices=[
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)'),
            ('CHF', 'Swiss Franc (CHF)'),
        ],
        default='USD',
        help_text="Currency for energy costs"
    )
    show_revenue_stats = models.BooleanField(
        default=True,
        help_text="Show mining revenue statistics (based on solo mining probability)"
    )

    # Cached network data (updated periodically)
    cached_btc_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=100000,
        help_text="Cached Bitcoin price in USD"
    )
    cached_network_hashrate = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=750,
        help_text="Cached network hashrate in EH/s"
    )
    cached_network_difficulty = models.DecimalField(
        max_digits=30,
        decimal_places=0,
        default=0,
        help_text="Cached network difficulty"
    )
    network_data_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When network data was last updated"
    )

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

    def get_notification_rules(self):
        """Merged notification rules with defaults (safe for missing/partial JSON)."""
        return merge_notification_rules(self.notification_rules)
