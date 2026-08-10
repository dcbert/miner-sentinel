"""Tests for unified /api/devices/, /api/mining/, /api/hardware/, /api/pool/ endpoints."""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Device, DeviceHardwareStats, DeviceMiningStats, PoolStats


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='u', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_create_device_unified(auth_client):
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
    # Release C: no legacy BitAxeDevice table
    assert not hasattr(__import__('api.models', fromlist=['Device']), 'BitAxeDevice')


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


@pytest.mark.django_db
def test_create_nmaxe_and_nerdnos_devices(auth_client):
    nmaxe = auth_client.post(
        '/api/devices/',
        {
            'device_id': 'nmaxeg2',
            'device_name': 'NMAxe Gamma 2',
            'make': 'nmaxe',
            'ip_address': '10.0.0.50',
            'is_active': True,
        },
        format='json',
    )
    assert nmaxe.status_code == 201
    assert nmaxe.data['make'] == 'nmaxe'
    assert nmaxe.data['protocol'] == Device.PROTOCOL_HTTP_NMAXE

    nerd = auth_client.post(
        '/api/devices/',
        {
            'device_id': 'nerd-1',
            'device_name': 'NerdNOS Metal',
            'make': 'nerdnos',
            'ip_address': '10.0.0.51',
            'is_active': True,
        },
        format='json',
    )
    assert nerd.status_code == 201
    assert nerd.data['make'] == 'nerdnos'
    assert nerd.data['protocol'] == Device.PROTOCOL_HTTP_NERDNOS

    listed = auth_client.get('/api/devices/')
    results = listed.data['results'] if isinstance(listed.data, dict) else listed.data
    makes = {r['make'] for r in results}
    assert 'nmaxe' in makes and 'nerdnos' in makes


@pytest.mark.django_db
def test_pool_api_latest_and_filter(auth_client):

    PoolStats.objects.create(
        pool_type=PoolStats.POOL_CKPOOL,
        pool_address='bc1q',
        recorded_at=timezone.now(),
        hashrate_1m_ghs=10.0,
        hashrate_1m_display='10G',
        workers=1,
        best_share=1e12,
        best_ever=2e12,
    )
    resp = auth_client.get('/api/pool/latest/')
    assert resp.status_code == 200
    assert resp.data['pool_address'] == 'bc1q'
    # display aliases used by mining dashboard
    assert resp.data['hashrate_1m'] == '10G'
    assert resp.data['bestshare'] == pytest.approx(1e12)
    resp2 = auth_client.get('/api/pool/?pool_type=ckpool')
    assert resp2.status_code == 200
    stats = auth_client.get('/api/pool/statistics/')
    assert stats.status_code == 200
    assert 'data_points' in stats.data
    trend = auth_client.get('/api/pool/hashrate_trend/')
    assert trend.status_code == 200
    assert isinstance(trend.data, list)


@pytest.mark.django_db
def test_device_crud_unified(auth_client):
    create = auth_client.post(
        '/api/devices/',
        {
            'device_id': 'crud-1',
            'device_name': 'CRUD Bitaxe',
            'make': 'bitaxe',
            'ip_address': '10.0.0.99',
            'is_active': True,
        },
        format='json',
    )
    assert create.status_code == 201
    device = Device.objects.get(make='bitaxe', device_id='crud-1')
    assert device.name == 'CRUD Bitaxe'

    listed = auth_client.get('/api/devices/?make=bitaxe&active_only=true')
    assert listed.status_code == 200
    results = listed.data['results'] if isinstance(listed.data, dict) else listed.data
    assert any(r['device_id'] == 'crud-1' for r in results)

    patched = auth_client.patch(
        f'/api/devices/{device.id}/',
        {'device_name': 'Renamed'},
        format='json',
    )
    assert patched.status_code == 200
    device.refresh_from_db()
    assert device.name == 'Renamed'

    deleted = auth_client.delete(f'/api/devices/{device.id}/')
    assert deleted.status_code in (200, 204)
    assert not Device.objects.filter(pk=device.id).exists()


def test_brand_shim_urls_removed():
    """Legacy /api/bitaxe/* and /api/avalon/* routes are not registered."""
    from django.urls import resolve, Resolver404

    for url in (
        '/api/bitaxe/devices/',
        '/api/bitaxe/mining/latest/',
        '/api/bitaxe/pool/latest/',
        '/api/avalon/devices/',
        '/api/avalon/dashboard/',
        '/api/avalon/mining-stats/',
    ):
        with pytest.raises(Resolver404):
            resolve(url)
