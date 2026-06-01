from rest_framework import serializers

from .models import AvalonDevice, BitAxeDevice, BitAxeHardwareLog, BitAxeMiningStats, BitAxePoolStats, BitAxeSystemInfo, CollectorSettings


class BitAxeDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BitAxeDevice
        fields = '__all__'


class BitAxeDeviceWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Bitaxe devices."""
    class Meta:
        model = BitAxeDevice
        fields = ['device_id', 'device_name', 'ip_address', 'is_active']


class AvalonDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvalonDevice
        fields = '__all__'


class AvalonDeviceWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Avalon devices."""
    class Meta:
        model = AvalonDevice
        fields = ['device_id', 'device_name', 'ip_address', 'is_active']


class BitAxeMiningStatsSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.device_name', read_only=True)

    class Meta:
        model = BitAxeMiningStats
        fields = '__all__'


class BitAxeHardwareLogSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.device_name', read_only=True)

    class Meta:
        model = BitAxeHardwareLog
        fields = '__all__'


class BitAxeSystemInfoSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.device_name', read_only=True)

    class Meta:
        model = BitAxeSystemInfo
        fields = '__all__'


class BitAxePoolStatsSerializer(serializers.ModelSerializer):
    lastshare_datetime = serializers.SerializerMethodField()
    authorised_datetime = serializers.SerializerMethodField()

    class Meta:
        model = BitAxePoolStats
        fields = '__all__'

    def get_lastshare_datetime(self, obj):
        """Convert Unix timestamp to ISO datetime string."""
        from datetime import datetime
        if obj.lastshare:
            return datetime.fromtimestamp(obj.lastshare).isoformat()
        return None

    def get_authorised_datetime(self, obj):
        """Convert Unix timestamp to ISO datetime string."""
        from datetime import datetime
        if obj.authorised:
            return datetime.fromtimestamp(obj.authorised).isoformat()
        return None


class CollectorSettingsSerializer(serializers.ModelSerializer):
    """Serializer for data collector settings."""
    # Virtual field to indicate if bot token is configured (without exposing the actual token)
    telegram_bot_token_configured = serializers.SerializerMethodField()
    # Virtual field for Discord webhook (sensitive, don't expose value)
    discord_webhook_url_configured = serializers.SerializerMethodField()

    class Meta:
        model = CollectorSettings
        fields = [
            'polling_interval_minutes',
            'device_check_interval_minutes',
            'pool_type',
            'ckpool_address',
            'ckpool_url',
            'publicpool_address',
            'publicpool_url',
            'telegram_enabled',
            'telegram_bot_token',
            'telegram_bot_token_configured',
            'telegram_chat_id',
            'discord_enabled',
            'discord_webhook_url',
            'discord_webhook_url_configured',
            # Cost analysis settings
            'energy_rate',
            'energy_currency',
            'show_revenue_stats',
            # Cached network data (read-only)
            'cached_btc_price',
            'cached_network_hashrate',
            'cached_network_difficulty',
            'network_data_updated_at',
            'updated_at',
            'created_at',
        ]
        read_only_fields = [
            'updated_at',
            'created_at',
            'telegram_bot_token_configured',
            'discord_webhook_url_configured',
            'cached_btc_price',
            'cached_network_hashrate',
            'cached_network_difficulty',
            'network_data_updated_at',
        ]
        extra_kwargs = {
            'telegram_bot_token': {'write_only': True},  # Never return the actual token
            'discord_webhook_url': {'write_only': True},  # Never return the actual webhook URL
        }

    def get_telegram_bot_token_configured(self, obj):
        """Return True if a bot token is configured."""
        return bool(obj.telegram_bot_token and obj.telegram_bot_token.strip())

    def get_discord_webhook_url_configured(self, obj):
        """Return True if a Discord webhook URL is configured."""
        return bool(obj.discord_webhook_url and obj.discord_webhook_url.strip())

    def update(self, instance, validated_data):
        """Handle sensitive fields - only update if a new value is provided."""
        # If telegram_bot_token is empty string or not provided, keep the existing value
        telegram_bot_token = validated_data.get('telegram_bot_token', None)
        if telegram_bot_token == '' or telegram_bot_token is None:
            validated_data.pop('telegram_bot_token', None)

        # Same for Discord webhook URL
        discord_webhook_url = validated_data.get('discord_webhook_url', None)
        if discord_webhook_url == '' or discord_webhook_url is None:
            validated_data.pop('discord_webhook_url', None)

        return super().update(instance, validated_data)
