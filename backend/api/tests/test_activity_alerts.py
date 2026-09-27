"""Tests for AlertEvent activity API + extended notification rules."""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import AlertEvent, CollectorSettings, Device, merge_notification_rules


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='activity-user', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestAlertEventApi:
    def test_list_and_acknowledge(self, auth_client):
        device = Device.objects.create(
            device_id='bx-1',
            name='Lab Bitaxe',
            make=Device.MAKE_BITAXE,
            protocol=Device.PROTOCOL_HTTP_AXEOS,
            ip_address='192.168.1.7',
        )
        ev = AlertEvent.objects.create(
            event_type='device_offline',
            severity=AlertEvent.SEVERITY_CRITICAL,
            device=device,
            device_make='bitaxe',
            device_key='bx-1',
            device_name='Lab Bitaxe',
            message='Lab Bitaxe went offline',
            fingerprint='device_offline:bitaxe:bx-1',
        )
        # Best difficulty must never inflate open problem counts
        AlertEvent.objects.create(
            event_type='best_difficulty',
            severity=AlertEvent.SEVERITY_INFO,
            device=device,
            device_make='bitaxe',
            device_key='bx-1',
            device_name='Lab Bitaxe',
            message='Lab Bitaxe set a new best share',
            fingerprint='best_difficulty:bitaxe:bx-1',
        )
        resp = auth_client.get('/api/activity/', {'open': 'true', 'kind': 'problem'})
        assert resp.status_code == 200
        assert resp.data['open_count'] >= 1
        ids = [r['id'] for r in resp.data['results']]
        assert ev.id in ids
        assert all(r['event_type'] != 'best_difficulty' for r in resp.data['results'])

        highlights = auth_client.get('/api/activity/', {'kind': 'highlight'})
        assert highlights.status_code == 200
        assert any(r['event_type'] == 'best_difficulty' for r in highlights.data['results'])

        ack = auth_client.post(f'/api/activity/{ev.id}/acknowledge/')
        assert ack.status_code == 200
        ev.refresh_from_db()
        assert ev.acknowledged_at is not None

    def test_snooze(self, auth_client):
        ev = AlertEvent.objects.create(
            event_type='temperature_high',
            severity=AlertEvent.SEVERITY_CRITICAL,
            message='Hot device',
            fingerprint='temperature_high:bitaxe:x',
            device_make='bitaxe',
            device_key='x',
        )
        resp = auth_client.post(f'/api/activity/{ev.id}/snooze/', {'minutes': 30}, format='json')
        assert resp.status_code == 200
        ev.refresh_from_db()
        assert ev.muted_until is not None
        assert ev.muted_until > timezone.now()

    def test_new_rules_in_settings(self, auth_client):
        resp = auth_client.get('/api/settings/collector/')
        assert resp.status_code == 200
        rules = resp.data['notification_rules']
        assert 'temperature_high' in rules
        assert 'fan_dead' in rules
        assert 'quiet_hours_enabled' in resp.data

    def test_quiet_hours_update(self, auth_client):
        resp = auth_client.post(
            '/api/settings/collector/',
            {
                'quiet_hours_enabled': True,
                'quiet_hours_start': '23:00',
                'quiet_hours_end': '06:30',
                'alert_repeat_minutes': 90,
                'polling_interval_minutes': 2,
            },
            format='json',
        )
        assert resp.status_code == 200
        settings = CollectorSettings.get_settings()
        assert settings.quiet_hours_enabled is True
        assert settings.quiet_hours_start == '23:00'
        assert settings.alert_repeat_minutes == 90


class TestMergeNewRules:
    def test_defaults(self):
        m = merge_notification_rules({})
        assert m['collector_down']['severity'] == 'critical'
        assert m['temperature_high']['threshold_c'] == 80.0
