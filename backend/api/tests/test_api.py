"""
Backend API test suite.
Covers: auth views, device CRUD, stats endpoints, analytics, collector settings.
Runs against SQLite in-memory via minersentinel.settings_test (MIGRATION_MODULES disabled).
"""
from unittest.mock import MagicMock, patch

import pytest
from api.models import (
    AvalonDevice,
    AvalonHardwareLogs,
    AvalonMiningStats,
    AvalonSystemInfo,
    BitAxeDevice,
    BitAxeHardwareLog,
    BitAxeMiningStats,
    BitAxePoolStats,
    BitAxeSystemInfo,
    CollectorSettings,
)
from django.contrib.auth.models import User
from django.utils import timezone

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='testpass123')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def bitaxe_device(db):
    return BitAxeDevice.objects.create(
        device_id='bitaxe-001',
        device_name='Test Bitaxe',
        ip_address='192.168.1.10',
        is_active=True,
    )


@pytest.fixture
def avalon_device(db):
    return AvalonDevice.objects.create(
        device_id='avalon-001',
        device_name='Test Avalon',
        ip_address='192.168.1.20',
        is_active=True,
    )


@pytest.fixture
def mining_stat(bitaxe_device):
    return BitAxeMiningStats.objects.create(
        device=bitaxe_device,
        recorded_at=timezone.now(),
        hashrate_ghs=450.5,
        shares_accepted=1000,
        shares_rejected=5,
        uptime_seconds=3600,
    )


@pytest.fixture
def hardware_log(bitaxe_device):
    return BitAxeHardwareLog.objects.create(
        device=bitaxe_device,
        recorded_at=timezone.now(),
        power_watts=15.5,
        temperature_c=65.0,
        fan_speed_rpm=4500,
    )


@pytest.fixture
def pool_stat(db):
    return BitAxePoolStats.objects.create(
        pool_address='bc1qtest',
        hashrate_1m='466G',
        hashrate_5m='460G',
        hashrate_1hr='455G',
        hashrate_1d='450G',
        hashrate_7d='445G',
        lastshare=1700000000,
        workers=2,
        shares=500000,
        bestshare=9876543.0,
        bestever=123456789,
        authorised=1699000000,
    )


@pytest.fixture
def avalon_mining_stat(avalon_device):
    return AvalonMiningStats.objects.create(
        device=avalon_device,
        recorded_at=timezone.now(),
        hashrate_ghs=6500.0,
        shares_accepted=2000,
        shares_rejected=10,
        uptime_seconds=7200,
        difficulty=1234567.0,
    )


@pytest.fixture
def avalon_hardware_log(avalon_device):
    return AvalonHardwareLogs.objects.create(
        device=avalon_device,
        recorded_at=timezone.now(),
        power_watts=130.0,
        temperature_c=65.0,
        fan_speed_rpm=1500,
        frequency_mhz=464.0,
        voltage=12.0,
    )


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuthViews:
    def test_csrf_token(self, api_client):
        resp = api_client.get('/api/auth/csrf/')
        assert resp.status_code == 200
        assert 'csrfToken' in resp.data

    def test_current_user_anonymous(self, api_client):
        resp = api_client.get('/api/auth/user/')
        assert resp.status_code == 200
        assert resp.data['authenticated'] is False

    def test_current_user_authenticated(self, auth_client):
        resp = auth_client.get('/api/auth/user/')
        assert resp.status_code == 200
        assert resp.data['authenticated'] is True
        assert resp.data['user']['username'] == 'testuser'

    def test_login_success(self, api_client, user):
        resp = api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'testpass123'})
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['user']['username'] == 'testuser'

    def test_login_invalid_credentials(self, api_client, user):
        resp = api_client.post('/api/auth/login/', {'username': 'testuser', 'password': 'wrongpass'})
        assert resp.status_code == 401
        assert 'error' in resp.data

    def test_login_missing_fields(self, api_client):
        resp = api_client.post('/api/auth/login/', {'username': 'testuser'})
        assert resp.status_code == 400

    def test_logout(self, auth_client):
        resp = auth_client.post('/api/auth/logout/')
        assert resp.status_code == 200
        assert resp.data['success'] is True


# ---------------------------------------------------------------------------
# BitAxe device CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBitAxeDeviceViewSet:
    def test_list_empty(self, auth_client):
        resp = auth_client.get('/api/bitaxe/devices/')
        assert resp.status_code == 200

    def test_create_device(self, auth_client):
        payload = {
            'device_id': 'bitaxe-new',
            'device_name': 'New Bitaxe',
            'ip_address': '192.168.1.99',
        }
        resp = auth_client.post('/api/bitaxe/devices/', payload, format='json')
        assert resp.status_code == 201
        assert resp.data['device_id'] == 'bitaxe-new'

    def test_retrieve_device(self, auth_client, bitaxe_device):
        resp = auth_client.get(f'/api/bitaxe/devices/{bitaxe_device.device_id}/')
        assert resp.status_code == 200
        assert resp.data['device_name'] == 'Test Bitaxe'

    def test_retrieve_nonexistent(self, auth_client):
        resp = auth_client.get('/api/bitaxe/devices/does-not-exist/')
        assert resp.status_code == 404

    def test_update_device(self, auth_client, bitaxe_device):
        resp = auth_client.patch(
            f'/api/bitaxe/devices/{bitaxe_device.device_id}/',
            {'device_name': 'Renamed Bitaxe'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['device_name'] == 'Renamed Bitaxe'

    def test_delete_device(self, auth_client, bitaxe_device):
        resp = auth_client.delete(f'/api/bitaxe/devices/{bitaxe_device.device_id}/')
        assert resp.status_code == 204

    def test_filter_active_only(self, auth_client, bitaxe_device):
        BitAxeDevice.objects.create(
            device_id='bitaxe-inactive',
            device_name='Inactive',
            ip_address='192.168.1.11',
            is_active=False,
        )
        resp = auth_client.get('/api/bitaxe/devices/?active_only=true')
        assert resp.status_code == 200
        ids = [d['device_id'] for d in resp.data['results']]
        assert 'bitaxe-001' in ids
        assert 'bitaxe-inactive' not in ids


# ---------------------------------------------------------------------------
# BitAxe mining stats tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBitAxeMiningStatsViewSet:
    def test_list(self, auth_client, mining_stat):
        resp = auth_client.get('/api/bitaxe/mining/')
        assert resp.status_code == 200

    def test_latest_empty(self, auth_client):
        resp = auth_client.get('/api/bitaxe/mining/latest/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_latest_with_data(self, auth_client, mining_stat):
        resp = auth_client.get('/api/bitaxe/mining/latest/')
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['hashrate_ghs'] == pytest.approx(450.5)

    def test_filter_by_device(self, auth_client, mining_stat, bitaxe_device):
        resp = auth_client.get(f'/api/bitaxe/mining/?device_id={bitaxe_device.device_id}')
        assert resp.status_code == 200

    def test_hashrate_trend(self, auth_client, mining_stat):
        resp = auth_client.get('/api/bitaxe/mining/hashrate_trend/')
        assert resp.status_code == 200

    def test_hashrate_trend_with_device_filter(self, auth_client, mining_stat, bitaxe_device):
        resp = auth_client.get(f'/api/bitaxe/mining/hashrate_trend/?device_id={bitaxe_device.device_id}')
        assert resp.status_code == 200

    def test_latest_device_no_stats(self, auth_client, bitaxe_device):
        # Device exists but has no mining stats → False branch of `if latest_stat:`
        resp = auth_client.get('/api/bitaxe/mining/latest/')
        assert resp.status_code == 200
        assert resp.data == []


# ---------------------------------------------------------------------------
# BitAxe hardware log tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBitAxeHardwareLogViewSet:
    def test_list(self, auth_client, hardware_log):
        resp = auth_client.get('/api/bitaxe/hardware/')
        assert resp.status_code == 200

    def test_latest_empty(self, auth_client):
        resp = auth_client.get('/api/bitaxe/hardware/latest/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_latest_with_data(self, auth_client, hardware_log):
        resp = auth_client.get('/api/bitaxe/hardware/latest/')
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['temperature_c'] == pytest.approx(65.0)

    def test_temperature_trend(self, auth_client, hardware_log):
        resp = auth_client.get('/api/bitaxe/hardware/temperature_trend/')
        assert resp.status_code == 200

    def test_filter_by_device(self, auth_client, hardware_log, bitaxe_device):
        resp = auth_client.get(f'/api/bitaxe/hardware/?device_id={bitaxe_device.device_id}')
        assert resp.status_code == 200

    def test_temperature_trend_with_device_filter(self, auth_client, hardware_log, bitaxe_device):
        resp = auth_client.get(f'/api/bitaxe/hardware/temperature_trend/?device_id={bitaxe_device.device_id}')
        assert resp.status_code == 200

    def test_latest_device_no_logs(self, auth_client, bitaxe_device):
        # Device exists but has no hardware logs → False branch of `if latest_log:`
        resp = auth_client.get('/api/bitaxe/hardware/latest/')
        assert resp.status_code == 200
        assert resp.data == []


# ---------------------------------------------------------------------------
# BitAxe pool stats tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBitAxePoolStatsViewSet:
    def test_list(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/')
        assert resp.status_code == 200

    def test_latest_empty(self, auth_client):
        resp = auth_client.get('/api/bitaxe/pool/latest/')
        assert resp.status_code == 404

    def test_latest_with_data(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/latest/')
        assert resp.status_code == 200
        assert resp.data['pool_address'] == 'bc1qtest'

    def test_latest_with_pool_address_filter(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/latest/?pool_address=bc1qtest')
        assert resp.status_code == 200

    def test_latest_with_unknown_pool_address(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/latest/?pool_address=bc1qunknown')
        assert resp.status_code == 404

    def test_statistics_empty(self, auth_client):
        resp = auth_client.get('/api/bitaxe/pool/statistics/')
        assert resp.status_code == 200
        assert resp.data['total_shares'] == 0
        assert resp.data['data_points'] == 0

    def test_statistics_with_data(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/statistics/')
        assert resp.status_code == 200
        assert resp.data['data_points'] == 1

    def test_hashrate_trend(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/hashrate_trend/')
        assert resp.status_code == 200

    def test_filter_by_pool_address(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/?pool_address=bc1qtest')
        assert resp.status_code == 200

    def test_hashrate_trend_with_pool_filter(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/hashrate_trend/?pool_address=bc1qtest')
        assert resp.status_code == 200

    def test_statistics_with_pool_filter(self, auth_client, pool_stat):
        resp = auth_client.get('/api/bitaxe/pool/statistics/?pool_address=bc1qtest')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Overview analytics tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOverviewAnalytics:
    def test_requires_auth(self, api_client):
        resp = api_client.get('/api/overview/analytics/')
        assert resp.status_code in (401, 403)

    def test_returns_structure(self, auth_client):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert 'overview' in resp.data
        assert 'mining' in resp.data
        assert 'hardware' in resp.data
        assert 'pool' in resp.data

    def test_with_devices(self, auth_client, bitaxe_device, avalon_device, mining_stat, hardware_log):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert resp.data['overview']['bitaxe_devices'] == 1
        assert resp.data['overview']['avalon_devices'] == 1

    def test_with_all_data(self, auth_client, bitaxe_device, avalon_device,
                           mining_stat, hardware_log, pool_stat,
                           avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert resp.data['mining']['current']['total_hashrate_ghs'] > 0


# ---------------------------------------------------------------------------
# Avalon device tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAvalonViews:
    def test_dashboard_stats_empty(self, auth_client):
        resp = auth_client.get('/api/avalon/dashboard/')
        assert resp.status_code == 200

    def test_dashboard_stats_with_devices(self, auth_client, avalon_device,
                                          avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/avalon/dashboard/')
        assert resp.status_code == 200

    def test_dashboard_stats_device_without_stats(self, auth_client, avalon_device):
        # Device exists but no mining stats or hardware logs → covers False branches
        resp = auth_client.get('/api/avalon/dashboard/')
        assert resp.status_code == 200
        assert resp.data['total_devices'] == 1

    def test_devices_list_empty(self, auth_client):
        resp = auth_client.get('/api/avalon/devices/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_devices_list_with_data(self, auth_client, avalon_device):
        resp = auth_client.get('/api/avalon/devices/')
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['device_id'] == 'avalon-001'

    def test_devices_create(self, auth_client):
        payload = {
            'device_id': 'avalon-new',
            'device_name': 'New Avalon',
            'ip_address': '192.168.1.50',
        }
        resp = auth_client.post('/api/avalon/devices/', payload, format='json')
        assert resp.status_code == 201
        assert resp.data['device_id'] == 'avalon-new'

    def test_device_detail(self, auth_client, avalon_device):
        resp = auth_client.get(f'/api/avalon/devices/{avalon_device.device_id}/')
        assert resp.status_code == 200
        assert resp.data['device_name'] == 'Test Avalon'

    def test_device_detail_not_found(self, auth_client):
        resp = auth_client.get('/api/avalon/devices/does-not-exist/')
        assert resp.status_code == 404

    def test_device_update(self, auth_client, avalon_device):
        # Avalon device detail view supports PUT (not PATCH)
        resp = auth_client.put(
            f'/api/avalon/devices/{avalon_device.device_id}/',
            {'device_id': 'avalon-001', 'device_name': 'Renamed Avalon', 'ip_address': '192.168.1.20'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['device_name'] == 'Renamed Avalon'

    def test_device_delete(self, auth_client, avalon_device):
        resp = auth_client.delete(f'/api/avalon/devices/{avalon_device.device_id}/')
        assert resp.status_code == 204

    def test_mining_stats_empty(self, auth_client):
        resp = auth_client.get('/api/avalon/mining-stats/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_mining_stats_with_data(self, auth_client, avalon_mining_stat):
        resp = auth_client.get('/api/avalon/mining-stats/')
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['hashrate_ghs'] == pytest.approx(6500.0)

    def test_hardware_logs_empty(self, auth_client):
        resp = auth_client.get('/api/avalon/hardware-logs/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_hardware_logs_with_data(self, auth_client, avalon_hardware_log):
        resp = auth_client.get('/api/avalon/hardware-logs/')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_hashrate_trends(self, auth_client, avalon_device, avalon_mining_stat):
        resp = auth_client.get('/api/avalon/hashrate-trends/')
        assert resp.status_code == 200

    def test_temperature_trends(self, auth_client, avalon_device, avalon_hardware_log):
        resp = auth_client.get('/api/avalon/temperature-trends/')
        assert resp.status_code == 200

    def test_mining_stats_filter_by_device(self, auth_client, avalon_device, avalon_mining_stat):
        resp = auth_client.get(f'/api/avalon/mining-stats/?device_id={avalon_device.device_id}')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_hardware_logs_filter_by_device(self, auth_client, avalon_device, avalon_hardware_log):
        resp = auth_client.get(f'/api/avalon/hardware-logs/?device_id={avalon_device.device_id}')
        assert resp.status_code == 200

    def test_device_detail_with_stats(self, auth_client, avalon_device,
                                      avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get(f'/api/avalon/devices/{avalon_device.device_id}/')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Collector settings tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCollectorSettings:
    def test_get_settings(self, auth_client):
        resp = auth_client.get('/api/settings/collector/')
        assert resp.status_code == 200
        assert 'polling_interval_minutes' in resp.data

    def test_update_settings(self, auth_client):
        resp = auth_client.post(
            '/api/settings/collector/',
            {'polling_interval_minutes': 30},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['settings']['polling_interval_minutes'] == 30

    def test_settings_singleton(self, db):
        s1 = CollectorSettings.get_settings()
        s2 = CollectorSettings.get_settings()
        assert s1.pk == s2.pk == 1

    def test_settings_update_not_duplicate(self, db):
        CollectorSettings.get_settings()
        CollectorSettings.get_settings()
        assert CollectorSettings.objects.count() == 1

    def test_update_settings_invalid(self, auth_client):
        resp = auth_client.post(
            '/api/settings/collector/',
            {'polling_interval_minutes': 'not-a-number'},
            format='json',
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModels:
    def test_bitaxe_device_str(self, bitaxe_device):
        assert 'Test Bitaxe' in str(bitaxe_device)
        assert 'bitaxe-001' in str(bitaxe_device)

    def test_mining_stat_str(self, mining_stat):
        assert 'Test Bitaxe' in str(mining_stat)

    def test_hardware_log_str(self, hardware_log):
        assert 'Test Bitaxe' in str(hardware_log)

    def test_pool_stat_convert_ghs(self):
        assert BitAxePoolStats._convert_hashrate_to_ghs('1G') == pytest.approx(1.0)
        assert BitAxePoolStats._convert_hashrate_to_ghs('500M') == pytest.approx(0.5)
        assert BitAxePoolStats._convert_hashrate_to_ghs('1T') == pytest.approx(1000.0)
        assert BitAxePoolStats._convert_hashrate_to_ghs('2.5G') == pytest.approx(2.5)
        assert BitAxePoolStats._convert_hashrate_to_ghs('') == 0.0
        assert BitAxePoolStats._convert_hashrate_to_ghs(None) == 0.0

    def test_pool_stat_save_converts_hashrate(self, db):
        stat = BitAxePoolStats.objects.create(
            pool_address='bc1qtest2',
            hashrate_1m='2G',
            hashrate_5m='1.5G',
            hashrate_1hr='1G',
            hashrate_1d='900M',
            hashrate_7d='800M',
            lastshare=1700000000,
            workers=1,
            shares=100000,
            bestshare=1234567.0,
            bestever=9876543,
            authorised=1699000000,
        )
        assert stat.hashrate_1m_ghs == pytest.approx(2.0)
        assert stat.hashrate_1d_ghs == pytest.approx(0.9)

    def test_avalon_device_str(self, avalon_device):
        assert 'Test Avalon' in str(avalon_device)

    def test_avalon_mining_stat_str(self, avalon_mining_stat):
        assert 'Test Avalon' in str(avalon_mining_stat)

    def test_avalon_hardware_log_str(self, avalon_hardware_log):
        assert 'Test Avalon' in str(avalon_hardware_log)

    def test_collector_settings_str(self, db):
        s = CollectorSettings.get_settings()
        assert 'Collector Settings' in str(s)

    def test_collector_settings_delete_noop(self, db):
        s = CollectorSettings.get_settings()
        result = s.delete()
        assert CollectorSettings.objects.filter(pk=1).exists()
        assert result == (0, {})

    def test_bitaxe_system_info_str(self, db):
        device = BitAxeDevice.objects.create(
            device_id='sys-001', device_name='SysDevice', ip_address='10.0.0.1'
        )
        info = BitAxeSystemInfo.objects.create(device=device, recorded_at=timezone.now())
        assert 'SysDevice' in str(info)

    def test_avalon_system_info_str(self, db):
        device = AvalonDevice.objects.create(
            device_id='av-sys-001', device_name='AvalonSys', ip_address='10.0.0.2'
        )
        info = AvalonSystemInfo.objects.create(device=device, recorded_at=timezone.now())
        assert 'AvalonSys' in str(info)

    def test_bitaxe_pool_stats_str(self, pool_stat):
        assert 'Pool Stats' in str(pool_stat)


# ---------------------------------------------------------------------------
# Additional fixtures for expanded test coverage
# ---------------------------------------------------------------------------

@pytest.fixture
def system_info(bitaxe_device):
    return BitAxeSystemInfo.objects.create(
        device=bitaxe_device,
        recorded_at=timezone.now(),
        asic_model='BM1368',
        version='2.0.0',
        hostname='bitaxe-001',
    )


@pytest.fixture
def mining_stat_with_diff(bitaxe_device):
    return BitAxeMiningStats.objects.create(
        device=bitaxe_device,
        recorded_at=timezone.now(),
        hashrate_ghs=450.5,
        shares_accepted=1000,
        shares_rejected=5,
        uptime_seconds=3600,
        best_difficulty=123456789,
        best_session_difficulty=9876543,
    )


@pytest.fixture
def hardware_log_with_efficiency(bitaxe_device):
    return BitAxeHardwareLog.objects.create(
        device=bitaxe_device,
        recorded_at=timezone.now(),
        power_watts=15.5,
        temperature_c=65.0,
        fan_speed_rpm=4500,
        efficiency_j_per_th=34.4,
    )


# ---------------------------------------------------------------------------
# BitAxeSystemInfo viewset tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBitAxeSystemInfoViewSet:
    def test_list_empty(self, auth_client):
        resp = auth_client.get('/api/bitaxe/system/')
        assert resp.status_code == 200

    def test_list_with_data(self, auth_client, system_info):
        resp = auth_client.get('/api/bitaxe/system/')
        assert resp.status_code == 200

    def test_filter_by_device(self, auth_client, system_info):
        resp = auth_client.get(f'/api/bitaxe/system/?device_id={system_info.device.device_id}')
        assert resp.status_code == 200

    def test_device_details_not_found(self, auth_client):
        resp = auth_client.get('/api/bitaxe/system/device/no-such-device/')
        assert resp.status_code == 404

    def test_device_details_found_empty(self, auth_client, bitaxe_device):
        resp = auth_client.get(f'/api/bitaxe/system/device/{bitaxe_device.device_id}/')
        assert resp.status_code == 200
        assert 'device' in resp.data
        assert resp.data['latest_mining'] is None
        assert resp.data['latest_hardware'] is None
        assert resp.data['latest_system'] is None

    def test_device_details_with_all_data(self, auth_client, bitaxe_device,
                                           mining_stat, hardware_log, system_info):
        resp = auth_client.get(f'/api/bitaxe/system/device/{bitaxe_device.device_id}/')
        assert resp.status_code == 200
        assert resp.data['latest_mining']['hashrate_ghs'] == pytest.approx(450.5)
        assert resp.data['latest_hardware']['temperature_c'] == pytest.approx(65.0)
        assert resp.data['latest_system']['asic_model'] == 'BM1368'


# ---------------------------------------------------------------------------
# Network data & poll trigger endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNetworkDataEndpoints:
    def test_get_network_data(self, auth_client):
        resp = auth_client.get('/api/settings/network-data/')
        assert resp.status_code == 200
        assert 'btc_price' in resp.data
        assert 'network_hashrate_ehs' in resp.data
        assert 'network_difficulty' in resp.data

    def test_get_network_data_requires_auth(self, api_client):
        resp = api_client.get('/api/settings/network-data/')
        assert resp.status_code in (401, 403)

    def test_refresh_network_data_failed_fetches(self, auth_client):
        with patch('requests.get') as mock_get:
            mock_get.return_value = MagicMock(ok=False)
            resp = auth_client.post('/api/settings/network-data/refresh/')
        assert resp.status_code == 200
        assert resp.data['success'] is True

    def test_refresh_network_data_connection_error(self, auth_client):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            resp = auth_client.post('/api/settings/network-data/refresh/')
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['errors'] is not None

    def test_refresh_network_data_successful(self, auth_client):
        price_ok = MagicMock(ok=True)
        price_ok.json.return_value = {'bitcoin': {'usd': 95000}}
        hashrate_ok = MagicMock(ok=True)
        hashrate_ok.json.return_value = {
            'currentHashrate': 650e18,
            'currentDifficulty': 95000000000000,
        }
        with patch('requests.get', side_effect=[price_ok, hashrate_ok]):
            resp = auth_client.post('/api/settings/network-data/refresh/')
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['data']['btc_price'] == pytest.approx(95000)

    def test_refresh_requires_auth(self, api_client):
        resp = api_client.post('/api/settings/network-data/refresh/')
        assert resp.status_code in (401, 403)

    def test_trigger_poll_service_unavailable(self, auth_client):
        import requests as req_module
        with patch('requests.post') as mock_post:
            mock_post.side_effect = req_module.exceptions.RequestException("Service down")
            resp = auth_client.post('/api/settings/collector/poll/')
        assert resp.status_code == 503

    def test_trigger_poll_service_failure_response(self, auth_client):
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(ok=False)
            resp = auth_client.post('/api/settings/collector/poll/')
        assert resp.status_code == 500

    def test_trigger_poll_success(self, auth_client):
        mock_resp = MagicMock(ok=True)
        mock_resp.json.return_value = {'status': 'ok', 'polled': 2}
        with patch('requests.post', return_value=mock_resp):
            resp = auth_client.post('/api/settings/collector/poll/')
        assert resp.status_code == 200
        assert resp.data['success'] is True


# ---------------------------------------------------------------------------
# Detailed analytics endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDetailedAnalytics:
    def test_requires_auth(self, api_client):
        resp = api_client.get('/api/analytics/detailed/')
        assert resp.status_code in (401, 403)

    def test_returns_structure_empty(self, auth_client):
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        for key in ('energy_analysis', 'best_difficulty_prediction', 'device_comparison',
                    'cost_analysis', 'efficiency_trends', 'predictions'):
            assert key in resp.data

    def test_with_devices_no_hardware(self, auth_client, bitaxe_device, avalon_device):
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        assert resp.data['device_comparison']['total_devices'] == 0

    def test_with_full_bitaxe_data(self, auth_client, bitaxe_device,
                                    mining_stat_with_diff, hardware_log_with_efficiency):
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        assert resp.data['energy_analysis']['current_power_watts'] > 0
        assert resp.data['device_comparison']['total_devices'] == 1
        assert resp.data['best_difficulty_prediction']['all_time_best_difficulty'] == 123456789

    def test_with_full_mixed_data(self, auth_client, bitaxe_device, avalon_device,
                                   mining_stat_with_diff, hardware_log_with_efficiency,
                                   avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        assert resp.data['device_comparison']['total_devices'] == 2

    def test_best_difficulty_avalon_wins(self, auth_client, avalon_device,
                                         avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        best = resp.data['best_difficulty_prediction']['all_time_best_difficulty']
        assert best > 0

    def test_with_custom_period_params(self, auth_client, bitaxe_device,
                                        mining_stat, hardware_log):
        resp = auth_client.get('/api/analytics/detailed/?hours=48&days=14')
        assert resp.status_code == 200

    def test_cost_analysis_no_revenue(self, auth_client):
        settings = CollectorSettings.get_settings()
        settings.show_revenue_stats = False
        settings.save()
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        assert 'mining_revenue' not in resp.data.get('cost_analysis', {})

    def test_cost_analysis_with_revenue_enabled(self, auth_client, bitaxe_device,
                                                 mining_stat_with_diff, hardware_log_with_efficiency):
        settings = CollectorSettings.get_settings()
        settings.show_revenue_stats = True
        settings.cached_network_hashrate = 750
        settings.save()
        resp = auth_client.get('/api/analytics/detailed/')
        assert resp.status_code == 200
        cost = resp.data['cost_analysis']
        assert 'mining_revenue' in cost
        assert 'profitability' in cost
        assert 'efficiency_metrics' in cost

    def test_predictions_with_hashrate_data(self, auth_client, bitaxe_device,
                                             mining_stat_with_diff, hardware_log_with_efficiency):
        resp = auth_client.get('/api/analytics/detailed/?hours=24&days=7')
        assert resp.status_code == 200
        pred = resp.data['best_difficulty_prediction']
        assert 'probability_to_beat_current_best' in pred
        assert '1_hour' in pred['probability_to_beat_current_best']
        assert '24_hours' in pred['probability_to_beat_current_best']
        assert '7_days' in pred['probability_to_beat_current_best']


# ---------------------------------------------------------------------------
# Avalon restart device tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAvalonRestartDevice:
    def test_restart_not_found(self, auth_client):
        resp = auth_client.post('/api/avalon/devices/no-such-device/restart/')
        assert resp.status_code == 404

    def test_restart_socket_failure(self, auth_client, avalon_device):
        with patch('socket.socket') as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.connect.side_effect = Exception("Connection refused")
            mock_sock_cls.return_value = mock_sock
            resp = auth_client.post(
                f'/api/avalon/devices/{avalon_device.device_id}/restart/'
            )
        assert resp.status_code == 500

    def test_restart_socket_success(self, auth_client, avalon_device):
        with patch('socket.socket') as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.recv.return_value = b'STATUS=S,Restart sent|'
            mock_sock_cls.return_value = mock_sock
            resp = auth_client.post(
                f'/api/avalon/devices/{avalon_device.device_id}/restart/'
            )
        assert resp.status_code == 200

    def test_restart_socket_no_status_s(self, auth_client, avalon_device):
        with patch('socket.socket') as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.recv.return_value = b'STATUS=E,Error|'
            mock_sock_cls.return_value = mock_sock
            resp = auth_client.post(
                f'/api/avalon/devices/{avalon_device.device_id}/restart/'
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Avalon views edge cases
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAvalonViewsEdgeCases:
    def test_device_lookup_by_numeric_pk(self, auth_client, avalon_device):
        resp = auth_client.get(f'/api/avalon/devices/{avalon_device.pk}/')
        assert resp.status_code == 200

    def test_device_lookup_by_invalid_string_id(self, auth_client):
        resp = auth_client.get('/api/avalon/devices/this-does-not-exist/')
        assert resp.status_code == 404

    def test_device_update_invalid_ip(self, auth_client, avalon_device):
        resp = auth_client.put(
            f'/api/avalon/devices/{avalon_device.device_id}/',
            {'device_id': 'avalon-001', 'device_name': 'Test', 'ip_address': 'not-an-ip'},
            format='json',
        )
        assert resp.status_code == 400

    def test_hashrate_trends_empty_data(self, auth_client):
        resp = auth_client.get('/api/avalon/hashrate-trends/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_temperature_trends_empty_data(self, auth_client):
        resp = auth_client.get('/api/avalon/temperature-trends/')
        assert resp.status_code == 200
        assert resp.data == []

    def test_hashrate_trends_with_data_and_filter(self, auth_client, avalon_device, avalon_mining_stat):
        resp = auth_client.get(
            f'/api/avalon/hashrate-trends/?device_id={avalon_device.device_id}&interval=30'
        )
        assert resp.status_code == 200

    def test_temperature_trends_with_data_and_filter(self, auth_client, avalon_device, avalon_hardware_log):
        resp = auth_client.get(
            f'/api/avalon/temperature-trends/?device_id={avalon_device.device_id}&interval=30'
        )
        assert resp.status_code == 200

    def test_mining_stats_with_custom_params(self, auth_client, avalon_mining_stat):
        resp = auth_client.get('/api/avalon/mining-stats/?limit=5&hours=48')
        assert resp.status_code == 200

    def test_hardware_logs_with_custom_params(self, auth_client, avalon_hardware_log):
        resp = auth_client.get('/api/avalon/hardware-logs/?limit=5&hours=48')
        assert resp.status_code == 200

    def test_dashboard_stats_with_full_avalon_data(self, auth_client, avalon_device,
                                                     avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/avalon/dashboard/')
        assert resp.status_code == 200
        assert resp.data['total_hashrate_ghs'] == pytest.approx(6500.0)

    def test_devices_create_invalid(self, auth_client):
        resp = auth_client.post(
            '/api/avalon/devices/',
            {'device_name': 'Bad'},  # Missing device_id and ip_address
            format='json',
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHelperFunctions:
    def test_format_difficulty_zero(self):
        from api.views import _format_difficulty
        assert _format_difficulty(0) == '0'
        assert _format_difficulty(None) == '0'

    def test_format_difficulty_small(self):
        from api.views import _format_difficulty
        assert _format_difficulty(500) == '500'
        assert _format_difficulty(999) == '999'

    def test_format_difficulty_kilo(self):
        from api.views import _format_difficulty
        result = _format_difficulty(1500)
        assert 'K' in result

    def test_format_difficulty_mega(self):
        from api.views import _format_difficulty
        result = _format_difficulty(1_500_000)
        assert 'M' in result

    def test_format_difficulty_giga(self):
        from api.views import _format_difficulty
        result = _format_difficulty(1_500_000_000)
        assert 'G' in result

    def test_format_difficulty_tera(self):
        from api.views import _format_difficulty
        result = _format_difficulty(1_500_000_000_000)
        assert 'T' in result

    def test_format_difficulty_peta(self):
        from api.views import _format_difficulty
        result = _format_difficulty(1_500_000_000_000_000)
        assert 'P' in result

    def test_format_time_duration_minutes(self):
        from api.views import _format_time_duration
        assert 'minutes' in _format_time_duration(0.5)

    def test_format_time_duration_hours(self):
        from api.views import _format_time_duration
        assert 'hours' in _format_time_duration(5)

    def test_format_time_duration_days(self):
        from api.views import _format_time_duration
        assert 'days' in _format_time_duration(48)

    def test_format_time_duration_weeks(self):
        from api.views import _format_time_duration
        assert 'weeks' in _format_time_duration(200)

    def test_format_time_duration_months(self):
        from api.views import _format_time_duration
        assert 'months' in _format_time_duration(800)  # 800h > 720h threshold

    def test_format_time_duration_years(self):
        from api.views import _format_time_duration
        assert 'years' in _format_time_duration(9000)


# ---------------------------------------------------------------------------
# Extended overview analytics tests (covers best-share + financial paths)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOverviewAnalyticsExtended:
    def test_with_bitaxe_best_share(self, auth_client, bitaxe_device, mining_stat_with_diff):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert resp.data['mining']['current']['best_share_difficulty'] == 123456789

    def test_with_avalon_best_share_only(self, auth_client, avalon_device, avalon_mining_stat):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert resp.data['mining']['current']['best_share_difficulty'] is not None

    def test_with_both_best_shares(self, auth_client, bitaxe_device, avalon_device,
                                    avalon_mining_stat, mining_stat_with_diff):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        # mining_stat_with_diff has best_difficulty=123456789, avalon has 1234567
        # bitaxe wins
        assert resp.data['mining']['current']['best_share_difficulty'] == 123456789

    def test_with_pool_stats_current(self, auth_client, bitaxe_device,
                                      mining_stat, hardware_log, pool_stat):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert 'current' in resp.data['pool']
        assert resp.data['pool']['current']['workers'] == 2

    def test_with_custom_hours_and_days(self, auth_client, bitaxe_device,
                                         avalon_device, mining_stat, hardware_log):
        resp = auth_client.get('/api/overview/analytics/?hours=48&days=14')
        assert resp.status_code == 200
        assert resp.data['overview']['data_collection_period_hours'] == 48
        assert resp.data['overview']['analysis_period_days'] == 14

    def test_financial_calculations(self, auth_client, bitaxe_device, avalon_device,
                                     mining_stat_with_diff, hardware_log_with_efficiency,
                                     avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        fin = resp.data['financial']
        assert 'expected_btc_per_day' in fin
        assert 'energy_cost_per_day_usd' in fin

    def test_hardware_health_calculations(self, auth_client, bitaxe_device, avalon_device,
                                           hardware_log, avalon_hardware_log):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        health = resp.data['hardware']['health']
        assert 'temperature_stability' in health
        assert 'power_efficiency_gh_per_watt' in health

    def test_trends_section_with_data(self, auth_client, bitaxe_device, avalon_device,
                                       mining_stat, hardware_log,
                                       avalon_mining_stat, avalon_hardware_log):
        resp = auth_client.get('/api/overview/analytics/')
        assert resp.status_code == 200
        assert 'trends' in resp.data
