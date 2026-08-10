"""
Serializers for unified Device / mining / hardware / system / pool models.
"""
from rest_framework import serializers

from .models import (
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)


class UnifiedMiningSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    # Numeric FK of the parent Device row (for list views)
    device = serializers.IntegerField(source='device_id', read_only=True)
    # Alias used by some fleet UIs
    difficulty = serializers.FloatField(source='best_difficulty', read_only=True)

    class Meta:
        model = DeviceMiningStats
        fields = [
            'id', 'device', 'device_name', 'device_id', 'recorded_at',
            'hashrate_ghs', 'shares_accepted', 'shares_rejected',
            'blocks_found', 'uptime_seconds',
            'best_difficulty', 'best_session_difficulty', 'difficulty',
            'pool_url', 'pool_user', 'created_at',
        ]


class UnifiedHardwareSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    device = serializers.IntegerField(source='device_id', read_only=True)

    class Meta:
        model = DeviceHardwareStats
        fields = [
            'id', 'device', 'device_name', 'device_id', 'recorded_at',
            'power_watts', 'efficiency_j_per_th', 'temperature_c',
            'fan_speed_rpm', 'voltage', 'frequency_mhz', 'created_at',
        ]


class UnifiedSystemSerializer(serializers.ModelSerializer):
    """Flatten common columns + vendor details for the device detail UI."""
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    device = serializers.IntegerField(source='device_id', read_only=True)

    asic_model = serializers.SerializerMethodField()
    board_version = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    firmware_version = serializers.CharField(read_only=True, allow_null=True)
    axe_os_version = serializers.SerializerMethodField()
    idf_version = serializers.SerializerMethodField()
    running_partition = serializers.SerializerMethodField()
    ssid = serializers.CharField(source='wifi_ssid', read_only=True, allow_null=True)
    wifi_status = serializers.SerializerMethodField()
    core_voltage = serializers.SerializerMethodField()
    core_voltage_actual = serializers.SerializerMethodField()
    expected_hashrate = serializers.FloatField(source='expected_hashrate_ghs', read_only=True, allow_null=True)
    pool_difficulty = serializers.SerializerMethodField()
    small_core_count = serializers.SerializerMethodField()
    vr_temp = serializers.SerializerMethodField()
    temp_target = serializers.SerializerMethodField()
    overheat_mode = serializers.SerializerMethodField()
    auto_fan_speed = serializers.SerializerMethodField()
    fan_speed_percent = serializers.SerializerMethodField()
    min_fan_speed = serializers.SerializerMethodField()
    max_power = serializers.SerializerMethodField()
    nominal_voltage = serializers.SerializerMethodField()
    overclock_enabled = serializers.SerializerMethodField()
    display_type = serializers.SerializerMethodField()
    display_rotation = serializers.SerializerMethodField()
    invert_screen = serializers.SerializerMethodField()
    display_timeout = serializers.SerializerMethodField()
    stratum_url = serializers.CharField(source='primary_pool_url', read_only=True, allow_null=True)
    stratum_port = serializers.SerializerMethodField()
    stratum_user = serializers.CharField(source='primary_pool_user', read_only=True, allow_null=True)
    fallback_stratum_url = serializers.CharField(source='fallback_pool_url', read_only=True, allow_null=True)
    fallback_stratum_port = serializers.SerializerMethodField()
    is_using_fallback = serializers.BooleanField(source='using_fallback_pool', read_only=True, allow_null=True)
    free_heap = serializers.SerializerMethodField()
    is_psram_available = serializers.SerializerMethodField()

    class Meta:
        model = DeviceSystemInfo
        fields = [
            'id', 'device', 'device_name', 'device_id', 'recorded_at',
            'asic_model', 'board_version', 'hostname', 'mac_address',
            'version', 'firmware_version', 'axe_os_version', 'idf_version', 'running_partition',
            'ssid', 'wifi_status', 'wifi_rssi',
            'core_voltage', 'core_voltage_actual', 'expected_hashrate', 'pool_difficulty', 'small_core_count',
            'vr_temp', 'temp_target', 'overheat_mode',
            'auto_fan_speed', 'fan_speed_percent', 'min_fan_speed',
            'max_power', 'nominal_voltage', 'overclock_enabled',
            'display_type', 'display_rotation', 'invert_screen', 'display_timeout',
            'stratum_url', 'stratum_port', 'stratum_user',
            'fallback_stratum_url', 'fallback_stratum_port', 'is_using_fallback',
            'free_heap', 'is_psram_available', 'created_at',
        ]

    def _d(self, obj, key, default=None):
        return (obj.details or {}).get(key, default)

    def get_asic_model(self, obj):
        return self._d(obj, 'asic_model') or obj.model_reported

    def get_board_version(self, obj):
        return self._d(obj, 'board_version')

    def get_version(self, obj):
        return self._d(obj, 'version') or obj.firmware_version

    def get_axe_os_version(self, obj):
        return self._d(obj, 'axe_os_version')

    def get_idf_version(self, obj):
        return self._d(obj, 'idf_version')

    def get_running_partition(self, obj):
        return self._d(obj, 'running_partition')

    def get_wifi_status(self, obj):
        return self._d(obj, 'wifi_status')

    def get_core_voltage(self, obj):
        return self._d(obj, 'core_voltage')

    def get_core_voltage_actual(self, obj):
        return self._d(obj, 'core_voltage_actual')

    def get_pool_difficulty(self, obj):
        return self._d(obj, 'pool_difficulty')

    def get_small_core_count(self, obj):
        return self._d(obj, 'small_core_count')

    def get_vr_temp(self, obj):
        return self._d(obj, 'vr_temp')

    def get_temp_target(self, obj):
        return self._d(obj, 'temp_target')

    def get_overheat_mode(self, obj):
        return self._d(obj, 'overheat_mode', 0)

    def get_auto_fan_speed(self, obj):
        return self._d(obj, 'auto_fan_speed', True)

    def get_fan_speed_percent(self, obj):
        return self._d(obj, 'fan_speed_percent')

    def get_min_fan_speed(self, obj):
        return self._d(obj, 'min_fan_speed')

    def get_max_power(self, obj):
        return self._d(obj, 'max_power')

    def get_nominal_voltage(self, obj):
        return self._d(obj, 'nominal_voltage')

    def get_overclock_enabled(self, obj):
        return self._d(obj, 'overclock_enabled', False)

    def get_display_type(self, obj):
        return self._d(obj, 'display_type')

    def get_display_rotation(self, obj):
        return self._d(obj, 'display_rotation', 0)

    def get_invert_screen(self, obj):
        return self._d(obj, 'invert_screen', False)

    def get_display_timeout(self, obj):
        return self._d(obj, 'display_timeout', -1)

    def get_stratum_port(self, obj):
        return self._d(obj, 'stratum_port')

    def get_fallback_stratum_port(self, obj):
        return self._d(obj, 'fallback_stratum_port')

    def get_free_heap(self, obj):
        return self._d(obj, 'free_heap')

    def get_is_psram_available(self, obj):
        return self._d(obj, 'is_psram_available', False)


class UnifiedPoolSerializer(serializers.ModelSerializer):
    """Pool stats with display-string aliases used by the mining dashboard."""
    hashrate_1m = serializers.CharField(source='hashrate_1m_display', read_only=True, allow_null=True)
    hashrate_5m = serializers.CharField(source='hashrate_5m_display', read_only=True, allow_null=True)
    hashrate_1hr = serializers.CharField(source='hashrate_1h_display', read_only=True, allow_null=True)
    hashrate_1d = serializers.CharField(source='hashrate_1d_display', read_only=True, allow_null=True)
    hashrate_7d = serializers.CharField(source='hashrate_7d_display', read_only=True, allow_null=True)
    lastshare = serializers.IntegerField(source='last_share_unix', read_only=True, allow_null=True)
    bestshare = serializers.FloatField(source='best_share', read_only=True, allow_null=True)
    bestever = serializers.FloatField(source='best_ever', read_only=True, allow_null=True)
    authorised = serializers.SerializerMethodField()
    lastshare_datetime = serializers.SerializerMethodField()
    authorised_datetime = serializers.SerializerMethodField()

    class Meta:
        model = PoolStats
        fields = [
            'id', 'pool_type', 'pool_address', 'recorded_at',
            'hashrate_1m', 'hashrate_5m', 'hashrate_1hr', 'hashrate_1d', 'hashrate_7d',
            'lastshare', 'workers', 'shares', 'bestshare', 'bestever', 'authorised',
            'hashrate_1m_ghs', 'hashrate_5m_ghs', 'hashrate_1h_ghs', 'hashrate_1d_ghs', 'hashrate_7d_ghs',
            'best_share', 'best_ever',
            'lastshare_datetime', 'authorised_datetime',
        ]

    def get_authorised(self, obj):
        if obj.authorised_unix is not None:
            return obj.authorised_unix
        return obj.pool_total_miners or 0

    def get_lastshare_datetime(self, obj):
        from datetime import datetime
        if obj.last_share_unix:
            return datetime.fromtimestamp(obj.last_share_unix).isoformat()
        if obj.last_share_at:
            return obj.last_share_at.isoformat()
        return None

    def get_authorised_datetime(self, obj):
        from datetime import datetime
        if obj.authorised_unix:
            return datetime.fromtimestamp(obj.authorised_unix).isoformat()
        return None
