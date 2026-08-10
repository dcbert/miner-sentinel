"""
Backend API test suite.
Covers: auth views, device CRUD, stats endpoints, analytics, collector settings.
Runs against SQLite in-memory via minersentinel.settings_test (MIGRATION_MODULES disabled).
"""
from unittest.mock import MagicMock, patch

import pytest
from api.models import (
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
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
    return Device.objects.create(
        device_id='bitaxe-001',
        name='Test Bitaxe',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='192.168.1.10',
        is_active=True,
    )


@pytest.fixture
def unified_bitaxe(bitaxe_device):
    return bitaxe_device


@pytest.fixture
def avalon_device(db):
    return Device.objects.create(
        device_id='avalon-001',
        name='Test Avalon',
        make=Device.MAKE_AVALON,
        protocol=Device.PROTOCOL_CGMINER_TCP,
        ip_address='192.168.1.20',
        port=4028,
        is_active=True,
    )


@pytest.fixture
def unified_avalon(avalon_device):
    return avalon_device


@pytest.fixture
def mining_stat(unified_bitaxe):
    return DeviceMiningStats.objects.create(
        device=unified_bitaxe,
        recorded_at=timezone.now(),
        hashrate_ghs=450.5,
        shares_accepted=1000,
        shares_rejected=5,
        uptime_seconds=3600,
        best_difficulty=1_000_000,
    )


@pytest.fixture
def hardware_log(unified_bitaxe):
    return DeviceHardwareStats.objects.create(
        device=unified_bitaxe,
        recorded_at=timezone.now(),
        power_watts=15.5,
        temperature_c=65.0,
        fan_speed_rpm=4500,
    )


@pytest.fixture
def pool_stat(db):
    return PoolStats.objects.create(
        pool_type=PoolStats.POOL_CKPOOL,
        pool_address='bc1qtest',
        recorded_at=timezone.now(),
        hashrate_1m_display='466G',
        hashrate_5m_display='460G',
        hashrate_1h_display='455G',
        hashrate_1d_display='450G',
        hashrate_7d_display='445G',
        hashrate_1m_ghs=466.0,
        hashrate_1d_ghs=450.0,
        last_share_unix=1700000000,
        workers=2,
        shares=500000,
        best_share=9876543.0,
        best_ever=123456789,
        authorised_unix=1699000000,
    )


@pytest.fixture
def avalon_mining_stat(unified_avalon):
    return DeviceMiningStats.objects.create(
        device=unified_avalon,
        recorded_at=timezone.now(),
        hashrate_ghs=6500.0,
        shares_accepted=2000,
        shares_rejected=10,
        uptime_seconds=7200,
        best_difficulty=1234567.0,
    )


@pytest.fixture
def avalon_hardware_log(unified_avalon):
    return DeviceHardwareStats.objects.create(
        device=unified_avalon,
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
        from api.migration_utils import convert_hashrate_str_to_ghs
        assert convert_hashrate_str_to_ghs('1G') == pytest.approx(1.0)
        assert convert_hashrate_str_to_ghs('500M') == pytest.approx(0.5)
        assert convert_hashrate_str_to_ghs('1T') == pytest.approx(1000.0)
        assert convert_hashrate_str_to_ghs('2.5G') == pytest.approx(2.5)
        assert convert_hashrate_str_to_ghs('') is None
        assert convert_hashrate_str_to_ghs(None) is None

    def test_pool_stat_create_unified(self, db):
        stat = PoolStats.objects.create(
            pool_type=PoolStats.POOL_CKPOOL,
            pool_address='bc1qtest2',
            recorded_at=timezone.now(),
            hashrate_1m_display='2G',
            hashrate_1d_display='900M',
            hashrate_1m_ghs=2.0,
            hashrate_1d_ghs=0.9,
            workers=1,
            shares=100000,
            best_share=1234567.0,
            best_ever=9876543,
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

    def test_device_system_info_str(self, db):
        device = Device.objects.create(
            device_id='sys-001',
            name='SysDevice',
            make=Device.MAKE_BITAXE,
            protocol=Device.PROTOCOL_HTTP_AXEOS,
            ip_address='10.0.0.1',
        )
        info = DeviceSystemInfo.objects.create(
            device=device, recorded_at=timezone.now(), hostname='sys'
        )
        assert 'SysDevice' in str(info) or 'sys' in str(info)

    def test_pool_stats_str(self, pool_stat):
        assert 'bc1qtest' in str(pool_stat) or 'ckpool' in str(pool_stat).lower() or 'GH/s' in str(pool_stat)


# ---------------------------------------------------------------------------
# Additional fixtures for expanded test coverage
# ---------------------------------------------------------------------------

@pytest.fixture
def mining_stat_with_diff(unified_bitaxe):
    return DeviceMiningStats.objects.create(
        device=unified_bitaxe,
        recorded_at=timezone.now(),
        hashrate_ghs=450.5,
        shares_accepted=1000,
        shares_rejected=5,
        uptime_seconds=3600,
        best_difficulty=123456789,
        best_session_difficulty=9876543,
    )


@pytest.fixture
def hardware_log_with_efficiency(unified_bitaxe):
    return DeviceHardwareStats.objects.create(
        device=unified_bitaxe,
        recorded_at=timezone.now(),
        power_watts=15.5,
        temperature_c=65.0,
        fan_speed_rpm=4500,
        efficiency_j_per_th=34.4,
    )


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
        # Single coherent window: hours is canonical; days is derived (ceil(hours/24))
        resp = auth_client.get('/api/overview/analytics/?hours=48&days=14')
        assert resp.status_code == 200
        assert resp.data['overview']['data_collection_period_hours'] == 48
        assert resp.data['overview']['analysis_period_days'] == 2

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
