from rest_framework import serializers

from .models import (
    CollectorSettings,
    Device,
    DEFAULT_NOTIFICATION_RULES,
    merge_notification_rules,
)


# Protocol defaults when creating via unified API
MAKE_PROTOCOL = {
    Device.MAKE_BITAXE: Device.PROTOCOL_HTTP_AXEOS,
    Device.MAKE_AVALON: Device.PROTOCOL_CGMINER_TCP,
    Device.MAKE_NMAXE: Device.PROTOCOL_HTTP_NMAXE,
    Device.MAKE_NERDNOS: Device.PROTOCOL_HTTP_NERDNOS,
}


class DeviceSerializer(serializers.ModelSerializer):
    """Unified device registry with device_name alias for frontend."""
    device_name = serializers.CharField(source='name')

    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'device_name', 'make', 'model', 'protocol',
            'ip_address', 'port', 'is_active', 'last_seen_at', 'error_message',
            'connection_config', 'created_at',
        ]
        read_only_fields = ['created_at', 'last_seen_at', 'error_message']


class DeviceWriteSerializer(serializers.ModelSerializer):
    """Create/update unified device; accepts device_name."""
    device_name = serializers.CharField(source='name')
    protocol = serializers.CharField(required=False, allow_blank=True)
    port = serializers.IntegerField(required=False, allow_null=True)
    make = serializers.CharField(required=False)

    class Meta:
        model = Device
        fields = [
            'device_id', 'device_name', 'make', 'model', 'protocol',
            'ip_address', 'port', 'is_active',
        ]

    def validate_make(self, value):
        allowed = {c[0] for c in Device.MAKE_CHOICES}
        if value not in allowed:
            raise serializers.ValidationError(f'Unsupported make: {value}')
        return value

    def create(self, validated_data):
        make = validated_data.get('make')
        if not make:
            raise serializers.ValidationError({'make': 'This field is required.'})
        if not validated_data.get('protocol'):
            validated_data['protocol'] = MAKE_PROTOCOL.get(make, Device.PROTOCOL_CUSTOM)
        if make == Device.MAKE_AVALON and not validated_data.get('port'):
            validated_data['port'] = 4028
        return super().create(validated_data)

    def update(self, instance, validated_data):
        make = validated_data.get('make', instance.make)
        if 'protocol' in validated_data and not validated_data['protocol']:
            validated_data['protocol'] = MAKE_PROTOCOL.get(make, instance.protocol)
        return super().update(instance, validated_data)


class CollectorSettingsSerializer(serializers.ModelSerializer):
    """Serializer for data collector settings."""
    telegram_bot_token_configured = serializers.SerializerMethodField()
    discord_webhook_url_configured = serializers.SerializerMethodField()
    notification_rules = serializers.JSONField(required=False)

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
            'notification_rules',
            'energy_rate',
            'energy_currency',
            'show_revenue_stats',
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
            'telegram_bot_token': {'write_only': True},
            'discord_webhook_url': {'write_only': True},
        }

    def get_telegram_bot_token_configured(self, obj):
        return bool(obj.telegram_bot_token and obj.telegram_bot_token.strip())

    def get_discord_webhook_url_configured(self, obj):
        return bool(obj.discord_webhook_url and obj.discord_webhook_url.strip())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['notification_rules'] = instance.get_notification_rules()
        data['notification_rule_defaults'] = DEFAULT_NOTIFICATION_RULES
        return data

    def validate_notification_rules(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Must be an object')
        return merge_notification_rules(value)

    def update(self, instance, validated_data):
        telegram_bot_token = validated_data.get('telegram_bot_token', None)
        if telegram_bot_token == '' or telegram_bot_token is None:
            validated_data.pop('telegram_bot_token', None)

        discord_webhook_url = validated_data.get('discord_webhook_url', None)
        if discord_webhook_url == '' or discord_webhook_url is None:
            validated_data.pop('discord_webhook_url', None)

        return super().update(instance, validated_data)
