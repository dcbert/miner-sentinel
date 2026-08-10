"""Tests for safe query-param parsing and invalid hours/days handling."""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from api.analytics_unified import _parse_int_param as analytics_parse
from api.views import _parse_int_param as views_parse


@pytest.mark.parametrize('parser', [views_parse, analytics_parse])
class TestParseIntParam:
    def test_valid(self, parser):
        assert parser('24', 1) == 24
        assert parser(7, 1) == 7

    def test_invalid_falls_back(self, parser):
        assert parser('abc', 24) == 24
        assert parser(None, 24) == 24
        assert parser('', 24) == 24
        assert parser('3.5', 24) == 24  # int('3.5') raises ValueError

    def test_clamps_min(self, parser):
        assert parser('0', 24, min_value=1) == 1
        assert parser('-5', 24, min_value=1) == 1

    def test_clamps_max(self, parser):
        assert parser('99999', 24, min_value=1, max_value=100) == 100


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='param-user', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestAnalyticsInvalidParams:
    def test_overview_invalid_hours_does_not_500(self, auth_client):
        resp = auth_client.get('/api/overview/analytics/?hours=not-a-number&days=also-bad')
        assert resp.status_code == 200
        assert 'overview' in resp.data
        # Defaults applied
        assert resp.data['overview']['data_collection_period_hours'] == 24
        assert resp.data['overview']['analysis_period_days'] == 7

    def test_overview_clamps_huge_window(self, auth_client):
        resp = auth_client.get('/api/overview/analytics/?hours=999999&days=9999')
        assert resp.status_code == 200
        assert resp.data['overview']['data_collection_period_hours'] == 24 * 90
        assert resp.data['overview']['analysis_period_days'] == 90

    def test_detailed_invalid_hours_does_not_500(self, auth_client):
        resp = auth_client.get('/api/analytics/detailed/?hours=xyz&days=nope')
        assert resp.status_code == 200
        assert 'energy_analysis' in resp.data or 'cost_analysis' in resp.data


@pytest.mark.django_db
class TestPoolAndTrendInvalidParams:
    def test_pool_hashrate_trend_invalid_hours(self, auth_client):
        resp = auth_client.get('/api/bitaxe/pool/hashrate_trend/?hours=bad')
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_pool_statistics_invalid_days(self, auth_client):
        resp = auth_client.get('/api/bitaxe/pool/statistics/?days=nope')
        assert resp.status_code == 200
        assert 'data_points' in resp.data

    def test_bitaxe_hashrate_trend_invalid_hours(self, auth_client):
        resp = auth_client.get('/api/bitaxe/mining/hashrate_trend/?hours=abc')
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_avalon_mining_stats_invalid_hours(self, auth_client):
        resp = auth_client.get('/api/avalon/mining-stats/?hours=oops&limit=nope')
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
