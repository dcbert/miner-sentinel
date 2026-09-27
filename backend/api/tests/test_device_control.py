"""Tests for device control API, capabilities, advisor, and export."""

from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from api.models import AlertEvent, Device
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='ctrluser', password='testpass123')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def online_bitaxe(db):
    return Device.objects.create(
        device_id='bitaxe-lab-7',
        name='Bitaxe Lab',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='192.168.1.7',
        port=80,
        is_active=True,
        last_seen_at=timezone.now(),
        error_message=None,
    )


@pytest.fixture
def online_avalon(db):
    return Device.objects.create(
        device_id='avalon-mini-3s',
        name='Avalon Mini 3s',
        make=Device.MAKE_AVALON,
        protocol=Device.PROTOCOL_CGMINER_TCP,
        ip_address='192.168.1.11',
        port=4028,
        is_active=True,
        last_seen_at=timezone.now(),
    )


@pytest.fixture
def offline_bitaxe(db):
    return Device.objects.create(
        device_id='bitaxe-offline',
        name='Offline Bitaxe',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='192.168.1.99',
        is_active=True,
        error_message='Connection refused',
        last_seen_at=timezone.now() - timedelta(hours=2),
    )


class TestDeviceCapabilities:
    def test_bitaxe_capabilities(self, auth_client, online_bitaxe):
        resp = auth_client.get('/api/devices/bitaxe/bitaxe-lab-7/capabilities/')
        assert resp.status_code == 200
        assert resp.data['capabilities']['reboot'] is True
        assert resp.data['capabilities']['pause'] is True
        assert resp.data['offline'] is False

    def test_avalon_capabilities(self, auth_client, online_avalon):
        resp = auth_client.get('/api/devices/avalon/avalon-mini-3s/capabilities/')
        assert resp.status_code == 200
        assert resp.data['capabilities']['workmode'] is True
        assert resp.data['capabilities']['set_pool'] is False
        assert resp.data['capabilities']['frequency'] is False
        assert resp.data['capabilities']['voltage'] is False


class TestDeviceControl:
    @patch('requests.post')
    def test_reboot_proxies_and_logs(self, mock_post, auth_client, online_bitaxe):
        mock_post.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=lambda: {'ok': True, 'action': 'reboot', 'event_type': 'user_reboot'},
        )
        resp = auth_client.post(
            '/api/devices/bitaxe/bitaxe-lab-7/control/',
            {'action': 'reboot', 'params': {}},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['ok'] is True
        assert AlertEvent.objects.filter(event_type='user_reboot', device=online_bitaxe).exists()

    def test_control_rejects_offline(self, auth_client, offline_bitaxe):
        resp = auth_client.post(
            '/api/devices/bitaxe/bitaxe-offline/control/',
            {'action': 'reboot'},
            format='json',
        )
        assert resp.status_code == 409

    def test_control_rejects_unsupported(self, auth_client, online_avalon):
        resp = auth_client.post(
            '/api/devices/avalon/avalon-mini-3s/control/',
            {'action': 'pause'},
            format='json',
        )
        assert resp.status_code == 400

    @patch('requests.post')
    def test_fan_control(self, mock_post, auth_client, online_bitaxe):
        mock_post.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=lambda: {'ok': True, 'action': 'fan'},
        )
        resp = auth_client.post(
            '/api/devices/bitaxe/bitaxe-lab-7/control/',
            {'action': 'fan', 'params': {'percent': 80, 'auto': False}},
            format='json',
        )
        assert resp.status_code == 200
        body = mock_post.call_args[1]['json']
        assert body['action'] == 'fan'
        assert body['params']['percent'] == 80


class TestAdvisorAndExport:
    def test_advisor_lists_offline(self, auth_client, offline_bitaxe):
        resp = auth_client.get('/api/advisor/')
        assert resp.status_code == 200
        kinds = [s['kind'] for s in resp.data['suggestions']]
        assert 'device_offline' in kinds

    def test_export_csv(self, auth_client, online_bitaxe):
        resp = auth_client.get('/api/export/inventory.csv')
        assert resp.status_code == 200
        assert 'text/csv' in resp['Content-Type']
        assert b'bitaxe-lab-7' in resp.content

    def test_push_channels_status(self, auth_client):
        resp = auth_client.get('/api/settings/push-channels/')
        assert resp.status_code == 200
        assert resp.data['web_push']['status'] == 'deferred'
        assert resp.data['ntfy']['available'] is True
        assert resp.data['gotify']['available'] is True
        assert resp.data['webhook']['available'] is True
        assert resp.data['ntfy']['status'] == 'off'


class TestStratumCompare:
    def test_stratum_compare(self, auth_client, online_bitaxe):
        from api.models import DeviceSystemInfo, PoolStats
        from django.utils import timezone

        DeviceSystemInfo.objects.create(
            device=online_bitaxe,
            recorded_at=timezone.now(),
            primary_pool_url='stratum+tcp://eusolo.ckpool.org:3333',
            primary_pool_user='bc1qtest',
            fallback_pool_url='stratum+tcp://backup.example:3333',
            using_fallback_pool=False,
        )
        PoolStats.objects.create(
            pool_type='ckpool',
            pool_address='bc1qtest',
            recorded_at=timezone.now(),
            hashrate_1m_ghs=100.0,
            workers=1,
        )
        resp = auth_client.get('/api/pool/stratum-compare/')
        assert resp.status_code == 200
        assert resp.data['selected_pool']['pool_type'] == 'ckpool'
        assert resp.data['selected_pool']['latest'] is not None
        devices = resp.data['devices']
        assert any(d['device_id'] == online_bitaxe.device_id for d in devices)
        row = next(d for d in devices if d['device_id'] == online_bitaxe.device_id)
        assert row['matches_selected_pool_type'] is True
        assert 'ckpool' in (row['stratum_host'] or '')


class TestRetentionSettings:
    def test_retention_fields_roundtrip(self, auth_client):
        from api.models import CollectorSettings

        s = CollectorSettings.get_settings()
        s.metrics_retention_days = 30
        s.alert_retention_days = 180
        s.ntfy_enabled = True
        s.ntfy_url = 'https://ntfy.sh/lab'
        s.save()

        resp = auth_client.get('/api/settings/collector/')
        assert resp.status_code == 200
        assert resp.data['metrics_retention_days'] == 30
        assert resp.data['alert_retention_days'] == 180
        assert resp.data['ntfy_enabled'] is True
        assert resp.data['ntfy_url'] == 'https://ntfy.sh/lab'

    def test_prune_command(self, db):
        from datetime import timedelta
        from io import StringIO

        from django.core.management import call_command
        from django.utils import timezone

        from api.models import (
            AlertEvent,
            CollectorSettings,
            Device,
            DeviceMiningStats,
            PoolStats,
        )

        settings = CollectorSettings.get_settings()
        settings.metrics_retention_days = 7
        settings.alert_retention_days = 7
        settings.save()

        device = Device.objects.create(
            device_id='old-dev',
            name='Old',
            make='bitaxe',
            ip_address='10.0.0.9',
            is_active=True,
        )
        old = timezone.now() - timedelta(days=30)
        DeviceMiningStats.objects.create(
            device=device,
            recorded_at=old,
            hashrate_ghs=1.0,
        )
        DeviceMiningStats.objects.create(
            device=device,
            recorded_at=timezone.now(),
            hashrate_ghs=2.0,
        )
        PoolStats.objects.create(
            pool_type='ckpool',
            pool_address='x',
            recorded_at=old,
            hashrate_1m_ghs=1.0,
        )
        AlertEvent.objects.create(
            event_type='device_offline',
            severity='critical',
            message='old',
            fingerprint='old-fp',
            created_at=old,
            resolved_at=old,
        )
        AlertEvent.objects.create(
            event_type='device_offline',
            severity='critical',
            message='open',
            fingerprint='open-fp',
            created_at=old,
        )

        out = StringIO()
        call_command('prune_retention', stdout=out)
        assert DeviceMiningStats.objects.count() == 1
        assert PoolStats.objects.count() == 0
        assert AlertEvent.objects.filter(fingerprint='old-fp').count() == 0
        assert AlertEvent.objects.filter(fingerprint='open-fp').count() == 1


class TestSeedLabDevices:
    def test_seed_command(self, db):
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('seed_lab_devices', stdout=out)
        assert Device.objects.filter(ip_address='192.168.1.7').exists()
        assert Device.objects.filter(ip_address='192.168.1.11').exists()
        assert Device.objects.filter(ip_address='192.168.1.12').exists()
        # Idempotent
        call_command('seed_lab_devices', stdout=out)
        assert Device.objects.filter(ip_address='192.168.1.7').count() == 1
