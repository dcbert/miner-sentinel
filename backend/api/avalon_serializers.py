"""
Avalon Nano 3s API serializers for Django REST Framework
"""

from rest_framework import serializers

from .models import AvalonDevice, AvalonHardwareLogs, AvalonMiningStats, AvalonSystemInfo


class AvalonDeviceSerializer(serializers.ModelSerializer):
    """Serializer for Avalon device registry."""

    class Meta:
        model = AvalonDevice
        fields = [
            'id', 'device_id', 'device_name', 'ip_address',
            'is_active', 'last_seen_at', 'error_message', 'created_at'
        ]


class AvalonMiningStatsSerializer(serializers.ModelSerializer):
    """Serializer for Avalon mining statistics."""
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)

    class Meta:
        model = AvalonMiningStats
        fields = [
            'id', 'device', 'device_name', 'device_id', 'recorded_at',
            'hashrate_ghs', 'shares_accepted', 'shares_rejected',
            'blocks_found', 'uptime_seconds', 'difficulty',
            'pool_url', 'pool_user', 'created_at'
        ]


class AvalonHardwareLogsSerializer(serializers.ModelSerializer):
    """Serializer for Avalon hardware monitoring data."""
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)

    class Meta:
        model = AvalonHardwareLogs
        fields = [
            'id', 'device', 'device_name', 'device_id', 'recorded_at',
            'power_watts', 'efficiency_j_per_th', 'temperature_c',
            'fan_speed_rpm', 'voltage', 'frequency_mhz', 'created_at'
        ]


class AvalonSystemInfoSerializer(serializers.ModelSerializer):
    """Serializer for Avalon system information."""
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)

    class Meta:
        model = AvalonSystemInfo
        fields = [
            'id', 'device', 'device_name', 'device_id', 'recorded_at',
            'device_model', 'firmware_version', 'hardware_version',
            'serial_number', 'mac_address', 'ip_address', 'hostname',
            'wifi_ssid', 'wifi_signal_strength', 'primary_pool_url',
            'primary_pool_user', 'backup_pool_url', 'backup_pool_user',
            'active_pool', 'system_uptime_seconds', 'memory_usage_percent',
            'storage_usage_percent', 'target_frequency', 'target_voltage',
            'auto_tune_enabled', 'created_at'
        ]


class AvalonDeviceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Avalon device with related data."""
    latest_mining_stats = serializers.SerializerMethodField()
    latest_hardware_logs = serializers.SerializerMethodField()
    latest_system_info = serializers.SerializerMethodField()

    class Meta:
        model = AvalonDevice
        fields = [
            'id', 'device_id', 'device_name', 'ip_address',
            'is_active', 'last_seen_at', 'error_message', 'created_at',
            'latest_mining_stats', 'latest_hardware_logs', 'latest_system_info'
        ]

    def get_latest_mining_stats(self, obj):
        """Get the latest mining statistics for this device."""
        latest_stats = obj.mining_stats.first()
        if latest_stats:
            return AvalonMiningStatsSerializer(latest_stats).data
        return None

    def get_latest_hardware_logs(self, obj):
        """Get the latest hardware logs for this device."""
        latest_logs = obj.hardware_logs.first()
        if latest_logs:
            return AvalonHardwareLogsSerializer(latest_logs).data
        return None

    def get_latest_system_info(self, obj):
        """Get the latest system info for this device."""
        latest_info = obj.system_info.first()
        if latest_info:
            return AvalonSystemInfoSerializer(latest_info).data
        return None


class AvalonDashboardStatsSerializer(serializers.Serializer):
    """Serializer for Avalon dashboard statistics."""
    total_devices = serializers.IntegerField()
    online_devices = serializers.IntegerField()
    offline_devices = serializers.IntegerField()
    total_hashrate_ghs = serializers.FloatField()
    average_temperature = serializers.FloatField()
    total_power_watts = serializers.FloatField()
    average_efficiency = serializers.FloatField()
    total_shares_accepted = serializers.IntegerField()
    total_shares_rejected = serializers.IntegerField()
    devices = AvalonDeviceDetailSerializer(many=True)