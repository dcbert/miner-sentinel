"""
Historical dual-registry sync helpers (Release A/B).

Release C stores devices only in the unified ``devices`` table. These functions
are retained as no-op / thin wrappers so older call sites and docs stay importable;
prefer creating ``Device`` rows directly.
"""
from __future__ import annotations

from .models import Device


def sync_bitaxe_to_unified(legacy_or_device) -> Device:
    """Ensure a bitaxe Device row exists from a device-like object."""
    device_id = getattr(legacy_or_device, 'device_id', None)
    name = getattr(legacy_or_device, 'device_name', None) or getattr(legacy_or_device, 'name', None)
    ip = getattr(legacy_or_device, 'ip_address', None)
    is_active = getattr(legacy_or_device, 'is_active', True)
    last_seen_at = getattr(legacy_or_device, 'last_seen_at', None)
    error_message = getattr(legacy_or_device, 'error_message', None)
    obj, _ = Device.objects.update_or_create(
        make=Device.MAKE_BITAXE,
        device_id=device_id,
        defaults={
            'name': name or device_id,
            'model': None,
            'protocol': Device.PROTOCOL_HTTP_AXEOS,
            'ip_address': ip,
            'port': None,
            'is_active': is_active,
            'last_seen_at': last_seen_at,
            'error_message': error_message,
            'connection_config': {},
        },
    )
    return obj


def sync_avalon_to_unified(legacy_or_device) -> Device:
    """Ensure an avalon Device row exists from a device-like object."""
    device_id = getattr(legacy_or_device, 'device_id', None)
    name = getattr(legacy_or_device, 'device_name', None) or getattr(legacy_or_device, 'name', None)
    ip = getattr(legacy_or_device, 'ip_address', None)
    is_active = getattr(legacy_or_device, 'is_active', True)
    last_seen_at = getattr(legacy_or_device, 'last_seen_at', None)
    error_message = getattr(legacy_or_device, 'error_message', None)
    port = getattr(legacy_or_device, 'port', None) or 4028
    obj, _ = Device.objects.update_or_create(
        make=Device.MAKE_AVALON,
        device_id=device_id,
        defaults={
            'name': name or device_id,
            'model': None,
            'protocol': Device.PROTOCOL_CGMINER_TCP,
            'ip_address': ip,
            'port': port,
            'is_active': is_active,
            'last_seen_at': last_seen_at,
            'error_message': error_message,
            'connection_config': {},
        },
    )
    return obj


def delete_unified_device(make: str, device_id: str) -> None:
    Device.objects.filter(make=make, device_id=device_id).delete()
