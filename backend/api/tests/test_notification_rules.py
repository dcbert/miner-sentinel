"""Tests for notification rules merge + API surface."""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from api.models import CollectorSettings, merge_notification_rules


class TestMergeNotificationRules:
    def test_defaults_when_empty(self):
        m = merge_notification_rules({})
        assert m['device_offline']['enabled'] is True
        assert m['hashrate_stagnation']['threshold_collections'] == 3
        assert m['best_difficulty']['min_improvement_percent'] == 5.0

    def test_toggle_and_clamp(self):
        m = merge_notification_rules({
            'device_offline': {'enabled': False},
            'hashrate_stagnation': {'threshold_collections': 99, 'tolerance_ghs': -1},
            'best_difficulty': {'min_improvement_percent': 150},
        })
        assert m['device_offline']['enabled'] is False
        assert m['hashrate_stagnation']['threshold_collections'] == 20
        assert m['hashrate_stagnation']['tolerance_ghs'] == 0.0
        assert m['best_difficulty']['min_improvement_percent'] == 100.0


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='notify-user', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestNotificationRulesApi:
    def test_get_includes_merged_rules(self, auth_client):
        resp = auth_client.get('/api/settings/collector/')
        assert resp.status_code == 200
        rules = resp.data['notification_rules']
        assert 'device_offline' in rules
        assert 'label' in rules['device_offline']
        assert 'enabled' in rules['device_offline']

    def test_post_updates_rules(self, auth_client):
        resp = auth_client.post(
            '/api/settings/collector/',
            {
                'notification_rules': {
                    'device_offline': {'enabled': False},
                    'hashrate_stagnation': {
                        'enabled': True,
                        'threshold_collections': 5,
                        'tolerance_ghs': 0.5,
                    },
                }
            },
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        rules = resp.data['settings']['notification_rules']
        assert rules['device_offline']['enabled'] is False
        assert rules['hashrate_stagnation']['threshold_collections'] == 5

        stored = CollectorSettings.get_settings()
        assert stored.notification_rules['device_offline']['enabled'] is False

    def test_telegram_test_requires_credentials(self, auth_client):
        resp = auth_client.post('/api/settings/collector/test-telegram/', {}, format='json')
        assert resp.status_code == 400
        assert resp.data['success'] is False
