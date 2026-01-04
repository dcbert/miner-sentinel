from django.contrib import admin

from .models import AvalonDevice, BitAxeDevice, BitAxeHardwareLog, BitAxeMiningStats, BitAxePoolStats, BitAxeSystemInfo, CollectorSettings


@admin.register(BitAxeDevice)
class BitAxeDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'device_name', 'ip_address', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('device_id', 'device_name', 'ip_address')
    readonly_fields = ('created_at',)


@admin.register(BitAxeMiningStats)
class BitAxeMiningStatsAdmin(admin.ModelAdmin):
    list_display = ('device', 'recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected', 'blocks_found')
    list_filter = ('device', 'recorded_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'


@admin.register(BitAxeHardwareLog)
class BitAxeHardwareLogAdmin(admin.ModelAdmin):
    list_display = ('device', 'recorded_at', 'temperature_c', 'power_watts', 'efficiency_j_per_th')
    list_filter = ('device', 'recorded_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'


@admin.register(BitAxePoolStats)
class BitAxePoolStatsAdmin(admin.ModelAdmin):
    list_display = ('pool_address', 'recorded_at', 'hashrate_1m', 'hashrate_1d', 'workers', 'shares', 'bestshare')
    list_filter = ('recorded_at', 'pool_address')
    search_fields = ('pool_address',)
    readonly_fields = ('hashrate_1m_ghs', 'hashrate_1d_ghs')
    date_hierarchy = 'recorded_at'

    fieldsets = (
        ('Pool Information', {
            'fields': ('pool_address', 'recorded_at', 'workers')
        }),
        ('Hashrate Data', {
            'fields': ('hashrate_1m', 'hashrate_5m', 'hashrate_1hr', 'hashrate_1d', 'hashrate_7d',
                      'hashrate_1m_ghs', 'hashrate_1d_ghs')
        }),
        ('Shares & Performance', {
            'fields': ('shares', 'bestshare', 'bestever', 'lastshare', 'authorised')
        }),
    )


@admin.register(BitAxeSystemInfo)
class BitAxeSystemInfoAdmin(admin.ModelAdmin):
    list_display = ('device', 'recorded_at', 'hostname', 'asic_model', 'version', 'wifi_status')
    list_filter = ('device', 'recorded_at', 'asic_model')
    search_fields = ('hostname', 'mac_address', 'ssid')
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'

    fieldsets = (
        ('Device Information', {
            'fields': ('device', 'recorded_at', 'hostname', 'mac_address')
        }),
        ('Hardware', {
            'fields': ('asic_model', 'board_version', 'small_core_count', 'is_psram_available', 'free_heap')
        }),
        ('Software', {
            'fields': ('version', 'axe_os_version', 'idf_version', 'running_partition')
        }),
        ('Network', {
            'fields': ('ssid', 'wifi_status', 'wifi_rssi')
        }),
        ('Performance', {
            'fields': ('core_voltage', 'core_voltage_actual', 'expected_hashrate', 'pool_difficulty')
        }),
        ('Temperature Management', {
            'fields': ('vr_temp', 'temp_target', 'overheat_mode')
        }),
        ('Fan Control', {
            'fields': ('auto_fan_speed', 'fan_speed_percent', 'min_fan_speed')
        }),
        ('Power Settings', {
            'fields': ('max_power', 'nominal_voltage', 'overclock_enabled')
        }),
        ('Display', {
            'fields': ('display_type', 'display_rotation', 'invert_screen', 'display_timeout')
        }),
        ('Stratum', {
            'fields': ('stratum_url', 'stratum_port', 'stratum_user',
                      'fallback_stratum_url', 'fallback_stratum_port', 'is_using_fallback')
        }),
    )


@admin.register(AvalonDevice)
class AvalonDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'device_name', 'ip_address', 'is_active', 'last_seen_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('device_id', 'device_name', 'ip_address')
    readonly_fields = ('created_at', 'last_seen_at')


@admin.register(CollectorSettings)
class CollectorSettingsAdmin(admin.ModelAdmin):
    """Admin for data collector settings (singleton)."""
    list_display = ('pool_type', 'polling_interval_minutes', 'device_check_interval_minutes', 'telegram_enabled', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Polling Configuration', {
            'fields': ('polling_interval_minutes', 'device_check_interval_minutes')
        }),
        ('Pool Selection', {
            'fields': ('pool_type',),
            'description': 'Select which mining pool to use for statistics collection.'
        }),
        ('CKPool Configuration', {
            'fields': ('ckpool_address', 'ckpool_url'),
            'description': 'Settings for CKPool solo mining statistics.',
            'classes': ('collapse',)
        }),
        ('PublicPool Configuration', {
            'fields': ('publicpool_address', 'publicpool_url'),
            'description': 'Settings for local/self-hosted PublicPool instance.',
            'classes': ('collapse',)
        }),
        ('Telegram Notifications', {
            'fields': ('telegram_enabled', 'telegram_bot_token', 'telegram_chat_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Prevent adding more than one settings instance."""
        return not CollectorSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings."""
        return False
