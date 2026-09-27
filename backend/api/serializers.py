from rest_framework import serializers

from .models import (
    AlertEvent,
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
    ntfy_token_configured = serializers.SerializerMethodField()
    gotify_token_configured = serializers.SerializerMethodField()
    webhook_url_configured = serializers.SerializerMethodField()
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
            'btcpowlab_address',
            'btcpowlab_url',
            'parasite_address',
            'parasite_url',
            'telegram_enabled',
            'telegram_bot_token',
            'telegram_bot_token_configured',
            'telegram_chat_id',
            'discord_enabled',
            'discord_webhook_url',
            'discord_webhook_url_configured',
            'ntfy_enabled',
            'ntfy_url',
            'ntfy_token',
            'ntfy_token_configured',
            'gotify_enabled',
            'gotify_url',
            'gotify_token',
            'gotify_token_configured',
            'webhook_enabled',
            'webhook_url',
            'webhook_url_configured',
            'notification_rules',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
            'alert_repeat_minutes',
            'metrics_retention_days',
            'alert_retention_days',
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
            'ntfy_token_configured',
            'gotify_token_configured',
            'webhook_url_configured',
            'cached_btc_price',
            'cached_network_hashrate',
            'cached_network_difficulty',
            'network_data_updated_at',
        ]
        extra_kwargs = {
            'telegram_bot_token': {'write_only': True},
            'discord_webhook_url': {'write_only': True},
            'ntfy_token': {'write_only': True},
            'gotify_token': {'write_only': True},
            'webhook_url': {'write_only': True},
        }

    def get_telegram_bot_token_configured(self, obj):
        return bool(obj.telegram_bot_token and obj.telegram_bot_token.strip())

    def get_discord_webhook_url_configured(self, obj):
        return bool(obj.discord_webhook_url and obj.discord_webhook_url.strip())

    def get_ntfy_token_configured(self, obj):
        return bool(obj.ntfy_token and obj.ntfy_token.strip())

    def get_gotify_token_configured(self, obj):
        return bool(obj.gotify_token and obj.gotify_token.strip())

    def get_webhook_url_configured(self, obj):
        return bool(obj.webhook_url and obj.webhook_url.strip())

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

    def validate_quiet_hours_start(self, value):
        return self._validate_hhmm(value, 'quiet_hours_start')

    def validate_quiet_hours_end(self, value):
        return self._validate_hhmm(value, 'quiet_hours_end')

    def validate_alert_repeat_minutes(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError('Must be an integer')
        return max(5, min(1440, n))

    def validate_polling_interval_minutes(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError('Must be an integer')
        return max(1, min(60, n))

    def validate_metrics_retention_days(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError('Must be an integer')
        return max(0, min(3650, n))

    def validate_alert_retention_days(self, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError('Must be an integer')
        return max(0, min(3650, n))

    @staticmethod
    def _validate_hhmm(value, field_name):
        raw = (value or '').strip()
        try:
            parts = raw.split(':')
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return f'{h:02d}:{m:02d}'
        except (TypeError, ValueError, IndexError):
            raise serializers.ValidationError(f'{field_name} must be HH:MM')

    def update(self, instance, validated_data):
        for secret in (
            'telegram_bot_token',
            'discord_webhook_url',
            'ntfy_token',
            'gotify_token',
            'webhook_url',
        ):
            val = validated_data.get(secret, None)
            if val == '' or val is None:
                validated_data.pop(secret, None)

        return super().update(instance, validated_data)


class AlertEventSerializer(serializers.ModelSerializer):
    """Activity / alert journal entries."""
    is_open = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()

    class Meta:
        model = AlertEvent
        fields = [
            'id',
            'event_type',
            'severity',
            'device',
            'device_make',
            'device_key',
            'device_name',
            'message',
            'payload',
            'fingerprint',
            'created_at',
            'acknowledged_at',
            'resolved_at',
            'muted_until',
            'last_notified_at',
            'is_open',
            'is_muted',
        ]
        read_only_fields = fields

    def get_is_open(self, obj):
        return obj.is_open

    def get_is_muted(self, obj):
        return obj.is_muted

