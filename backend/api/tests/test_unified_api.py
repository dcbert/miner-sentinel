"""Tests for unified /api/devices/, /api/mining/, /api/hardware/ endpoints."""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Device, DeviceHardwareStats, DeviceMiningStats


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='u', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_create_device_unified_and_mirror(auth_client):
    resp = auth_client.post(
        '/api/devices/',
        {
            'device_id': 'fleet-1',
            'device_name': 'Fleet Bitaxe',
            'make': 'bitaxe',
            'ip_address': '10.0.0.10',
            'is_active': True,
        },
        format='json',
    )
    assert resp.status_code == 201
    assert resp.data['device_name'] == 'Fleet Bitaxe'
    assert resp.data['make'] == 'bitaxe'
    assert Device.objects.filter(make='bitaxe', device_id='fleet-1').exists()
    from api.models import BitAxeDevice
    assert BitAxeDevice.objects.filter(device_id='fleet-1').exists()


@pytest.mark.django_db
def test_list_devices_filter_make(auth_client):
    Device.objects.create(
        device_id='b1', name='B', make='bitaxe', protocol='http_axeos',
        ip_address='1.1.1.1', is_active=True,
    )
    Device.objects.create(
        device_id='a1', name='A', make='avalon', protocol='cgminer_tcp',
        ip_address='2.2.2.2', port=4028, is_active=True,
    )
    resp = auth_client.get('/api/devices/?make=avalon')
    assert resp.status_code == 200
    results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
    assert len(results) == 1
    assert results[0]['make'] == 'avalon'


@pytest.mark.django_db
def test_mining_and_hardware_latest(auth_client):
    d = Device.objects.create(
        device_id='b1', name='B', make='bitaxe', protocol='http_axeos',
        ip_address='1.1.1.1', is_active=True,
    )
    DeviceMiningStats.objects.create(
        device=d, recorded_at=timezone.now(), hashrate_ghs=100,
        shares_accepted=1, shares_rejected=0, uptime_seconds=1,
    )
    DeviceHardwareStats.objects.create(
        device=d, recorded_at=timezone.now(), temperature_c=50, power_watts=15,
    )
    m = auth_client.get('/api/mining/latest/')
    h = auth_client.get('/api/hardware/latest/')
    assert m.status_code == 200
    assert h.status_code == 200
    assert len(m.data) == 1
    assert m.data[0]['device_type'] == 'bitaxe'
    assert m.data[0]['hashrate_ghs'] == pytest.approx(100)
    assert len(h.data) == 1
    assert h.data[0]['temperature_c'] == pytest.approx(50)


@pytest.mark.django_db
def test_device_details_by_make_id(auth_client):
    d = Device.objects.create(
        device_id='b1', name='B', make='bitaxe', protocol='http_axeos',
        ip_address='1.1.1.1', is_active=True,
    )
    DeviceMiningStats.objects.create(
        device=d, recorded_at=timezone.now(), hashrate_ghs=200,
        shares_accepted=2, shares_rejected=0, uptime_seconds=10,
    )
    resp = auth_client.get('/api/devices/bitaxe/b1/details/')
    assert resp.status_code == 200
    assert resp.data['make'] == 'bitaxe'
    assert resp.data['latest_mining']['hashrate_ghs'] == pytest.approx(200)
