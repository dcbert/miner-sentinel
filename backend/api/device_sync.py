"""
Keep unified Device registry in sync with legacy BitAxeDevice / AvalonDevice rows.
"""
from __future__ import annotations

from .models import Device


def sync_bitaxe_to_unified(legacy) -> Device:
    """Create or update unified Device from a BitAxeDevice instance."""
    obj, _ = Device.objects.update_or_create(
        make=Device.MAKE_BITAXE,
        device_id=legacy.device_id,
        defaults={
            'name': legacy.device_name,
            'model': None,
            'protocol': Device.PROTOCOL_HTTP_AXEOS,
            'ip_address': legacy.ip_address,
            'port': None,
            'is_active': legacy.is_active,
            'last_seen_at': legacy.last_seen_at,
            'error_message': legacy.error_message,
            'connection_config': {},
        },
    )
    return obj


def sync_avalon_to_unified(legacy) -> Device:
    """Create or update unified Device from an AvalonDevice instance."""
    obj, _ = Device.objects.update_or_create(
        make=Device.MAKE_AVALON,
        device_id=legacy.device_id,
        defaults={
            'name': legacy.device_name,
            'model': None,
            'protocol': Device.PROTOCOL_CGMINER_TCP,
            'ip_address': legacy.ip_address,
            'port': 4028,
            'is_active': legacy.is_active,
            'last_seen_at': legacy.last_seen_at,
            'error_message': legacy.error_message,
            'connection_config': {},
        },
    )
    return obj


def delete_unified_device(make: str, device_id: str) -> None:
    Device.objects.filter(make=make, device_id=device_id).delete()
