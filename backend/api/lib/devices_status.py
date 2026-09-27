"""Server-side device online helpers (mirrors frontend/src/lib/devices.js)."""

from datetime import timedelta

from django.utils import timezone

ONLINE_MAX_AGE = timedelta(minutes=10)


def is_device_online_server(device) -> bool:
    if not device or not device.is_active:
        return False
    if device.error_message:
        return False
    if not device.last_seen_at:
        return False
    return device.last_seen_at >= timezone.now() - ONLINE_MAX_AGE
