"""Tests for device registry shims (Release C: unified Device only)."""
import pytest
from rest_framework.test import APIClient

from api.models import Device
from django.contrib.auth.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='u', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_bitaxe_create_via_shim(auth_client):
    resp = auth_client.post(
        '/api/bitaxe/devices/',
        {
            'device_id': 'sync-bx',
            'device_name': 'Synced Bitaxe',
            'ip_address': '192.168.0.10',
            'is_active': True,
        },
        format='json',
    )
    assert resp.status_code in (200, 201)
    u = Device.objects.get(make='bitaxe', device_id='sync-bx')
    assert u.name == 'Synced Bitaxe'
    assert u.protocol == Device.PROTOCOL_HTTP_AXEOS


@pytest.mark.django_db
def test_bitaxe_delete_via_shim(auth_client):
    Device.objects.create(
        device_id='del-bx',
        name='D',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='192.168.0.11',
    )
    resp = auth_client.delete('/api/bitaxe/devices/del-bx/')
    assert resp.status_code in (200, 204)
    assert not Device.objects.filter(make='bitaxe', device_id='del-bx').exists()


@pytest.mark.django_db
def test_avalon_create_via_shim(auth_client):
    resp = auth_client.post(
        '/api/avalon/devices/',
        {
            'device_id': 'sync-av',
            'device_name': 'Synced Avalon',
            'ip_address': '192.168.0.20',
            'is_active': True,
        },
        format='json',
    )
    assert resp.status_code in (200, 201)
    u = Device.objects.get(make='avalon', device_id='sync-av')
    assert u.port == 4028
