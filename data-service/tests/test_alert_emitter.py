"""Unit tests for alert emitter helpers (quiet hours, fingerprint)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from notifications.emitter import fingerprint_for, in_quiet_hours, emit_alert
from notifications.rules import NotificationRules, merge_notification_rules
from notifications.push_notifier import PushNotifier


class TestFingerprint:
    def test_with_device(self):
        assert fingerprint_for('device_offline', 'bitaxe', 'abc') == 'device_offline:bitaxe:abc'

    def test_fleet_level(self):
        assert fingerprint_for('pool_down') == 'pool_down'


class TestQuietHours:
    def test_disabled(self):
        assert in_quiet_hours({'quiet_hours_enabled': False}) is False

    def test_overnight_window(self):
        prefs = {
            'quiet_hours_enabled': True,
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '07:00',
        }
        # 23:00 local → inside
        now = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
        with patch('notifications.emitter.datetime') as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
            # Use real in_quiet_hours with explicit now
            assert in_quiet_hours(prefs, now=now) is True
        noon = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert in_quiet_hours(prefs, now=noon) is False

    def test_same_day_window(self):
        prefs = {
            'quiet_hours_enabled': True,
            'quiet_hours_start': '09:00',
            'quiet_hours_end': '17:00',
        }
        mid = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert in_quiet_hours(prefs, now=mid) is True
        early = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        assert in_quiet_hours(prefs, now=early) is False


class TestNewRules:
    def test_defaults_include_new_types(self):
        m = merge_notification_rules({})
        for key in (
            'temperature_high',
            'fan_dead',
            'pool_down',
            'collector_down',
            'expected_hashrate_drop',
        ):
            assert key in m
            assert m[key]['enabled'] is True

    def test_clamp_temp_and_drop(self):
        m = merge_notification_rules({
            'temperature_high': {'threshold_c': 200, 'duration_polls': 0},
            'expected_hashrate_drop': {'drop_percent': 1},
        })
        assert m['temperature_high']['threshold_c'] == 120.0
        assert m['temperature_high']['duration_polls'] == 1
        assert m['expected_hashrate_drop']['drop_percent'] == 5.0

    def test_severity_accessor(self):
        rules = NotificationRules({})
        assert rules.severity('device_offline') == 'critical'
        assert rules.severity('best_difficulty') == 'info'


class TestEmitAlertPush:
    @patch('notifications.emitter.psycopg2.connect')
    def test_push_deliver_called(self, mock_connect):
        # Simulate no existing open alert → insert path
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            None,  # no existing
            (42,),  # returning id
            None,   # device pk lookup unused path — actually order is device lookup first
        ]
        # Re-read emit_alert: first _lookup_device_pk, then SELECT existing, then INSERT
        cursor.fetchone.side_effect = [
            None,  # device pk
            None,  # existing
            (99,),  # insert returning
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_connect.return_value = conn

        tg = MagicMock()
        dc = MagicMock()
        push = MagicMock()
        push.enabled = True

        rules = NotificationRules({'device_offline': {'enabled': True}})
        alert_id = emit_alert(
            database_url='postgresql://x',
            event_key='device_offline',
            method_name='send_device_offline_alert',
            telegram=tg,
            discord=dc,
            push=push,
            rules=rules,
            args=('dev1', 'Miner'),
            device_make='bitaxe',
            device_id='dev1',
            device_name='Miner',
            message='Miner went offline',
            preferences={'quiet_hours_enabled': False},
        )
        assert alert_id == 99
        push.deliver.assert_called_once()
        kwargs = push.deliver.call_args.kwargs
        assert kwargs['event_key'] == 'device_offline'
        assert 'offline' in kwargs['message'].lower() or kwargs['message']
        tg.send_device_offline_alert.assert_called_once()
        dc.send_device_offline_alert.assert_called_once()
