from django.contrib import admin

from .models import (
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'name', 'make', 'protocol', 'ip_address', 'is_active', 'last_seen_at')
    list_filter = ('make', 'protocol', 'is_active')
    search_fields = ('device_id', 'name', 'ip_address')
    readonly_fields = ('created_at',)


@admin.register(DeviceMiningStats)
class DeviceMiningStatsAdmin(admin.ModelAdmin):
    list_display = ('device', 'recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected', 'best_difficulty')
    list_filter = ('device__make', 'recorded_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'


@admin.register(DeviceHardwareStats)
class DeviceHardwareStatsAdmin(admin.ModelAdmin):
    list_display = ('device', 'recorded_at', 'temperature_c', 'power_watts', 'efficiency_j_per_th')
    list_filter = ('device__make', 'recorded_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'


@admin.register(DeviceSystemInfo)
class DeviceSystemInfoAdmin(admin.ModelAdmin):
    list_display = ('device', 'recorded_at', 'hostname', 'model_reported', 'firmware_version')
    list_filter = ('device__make', 'recorded_at')
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'


@admin.register(PoolStats)
class UnifiedPoolStatsAdmin(admin.ModelAdmin):
    list_display = ('pool_type', 'pool_address', 'recorded_at', 'hashrate_1m_ghs', 'workers', 'best_share')
    list_filter = ('pool_type', 'recorded_at')
    search_fields = ('pool_address',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'recorded_at'


@admin.register(CollectorSettings)
class CollectorSettingsAdmin(admin.ModelAdmin):
    list_display = ('pool_type', 'polling_interval_minutes', 'telegram_enabled', 'discord_enabled', 'updated_at')
    readonly_fields = ('updated_at', 'created_at')
