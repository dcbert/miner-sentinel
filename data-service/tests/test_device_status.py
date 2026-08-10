"""Tests for device online/offline reachability helpers and transitions."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.avalon_collector import AvalonCollector
from collectors.bitaxe_collector import BitAxeCollector
from collectors.normalized import was_device_online


class TestWasDeviceOnline:
    def test_never_seen_is_offline(self):
        assert was_device_online(None, None) is False
        assert was_device_online('', None) is False

    def test_seen_without_error_is_online(self):
        seen = datetime(2026, 7, 1, tzinfo=timezone.utc)
        assert was_device_online(None, seen) is True
        assert was_device_online('', seen) is True
        assert was_device_online('   ', seen) is True

    def test_seen_with_error_is_offline(self):
        seen = datetime(2026, 7, 1, tzinfo=timezone.utc)
        assert was_device_online('connection refused', seen) is False
        assert was_device_online('timeout', seen) is False


class TestBitaxeStatusTransitions:
    def setup_method(self):
        self.collector = BitAxeCollector('postgresql://u:p@localhost/db', dual_write=False)
        self.collector.telegram_notifier = MagicMock()
        self.collector.discord_notifier = MagicMock()
        self.collector.writer = MagicMock()

    def _run_status(self, prev_error, last_seen, is_online, error=''):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (prev_error, last_seen, 'Bitaxe-1')
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        with patch.object(self.collector, 'get_db_connection', return_value=mock_conn):
            self.collector.update_device_status('bx-1', '10.0.0.1', is_online, error)
        return mock_cursor

    def test_offline_transition_alerts_once(self):
        seen = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        self._run_status(None, seen, False, 'timeout')
        self.collector.telegram_notifier.send_device_offline_alert.assert_called_once()
        self.collector.discord_notifier.send_device_offline_alert.assert_called_once()
        self.collector.telegram_notifier.send_device_online_alert.assert_not_called()

    def test_still_offline_does_not_re_alert(self):
        seen = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        self._run_status('previous timeout', seen, False, 'timeout again')
        self.collector.telegram_notifier.send_device_offline_alert.assert_not_called()
        self.collector.discord_notifier.send_device_offline_alert.assert_not_called()

    def test_online_recovery_alerts(self):
        seen = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        self._run_status('previous timeout', seen, True)
        self.collector.telegram_notifier.send_device_online_alert.assert_called_once()
        self.collector.discord_notifier.send_device_online_alert.assert_called_once()
        self.collector.telegram_notifier.send_device_offline_alert.assert_not_called()

    def test_still_online_does_not_alert(self):
        seen = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        self._run_status(None, seen, True)
        self.collector.telegram_notifier.send_device_offline_alert.assert_not_called()
        self.collector.telegram_notifier.send_device_online_alert.assert_not_called()

    def test_first_success_without_prior_seen_does_not_online_alert(self):
        """First successful poll on a never-seen device should not claim recovery."""
        self._run_status(None, None, True)
        self.collector.telegram_notifier.send_device_online_alert.assert_not_called()

    def test_is_active_was_not_used_as_reachability(self):
        """
        Regression: previously SELECT is_active meant every failed poll for an
        enabled device re-fired offline alerts, and recovery never fired.
        """
        seen = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        # Simulate prior offline state (error set) while device remains enabled
        self._run_status('timeout', seen, True)
        self.collector.telegram_notifier.send_device_online_alert.assert_called_once()


class TestAvalonStatusTransitions:
    def setup_method(self):
        self.collector = AvalonCollector('postgresql://u:p@localhost/db', dual_write=False)
        self.collector.telegram_notifier = MagicMock()
        self.collector.discord_notifier = MagicMock()
        self.collector.writer = MagicMock()

    def test_offline_transition_alerts(self):
        mock_cursor = MagicMock()
        seen = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_cursor.fetchone.return_value = (None, seen, 'Avalon-1')
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        with patch.object(self.collector, 'get_db_connection', return_value=mock_conn):
            self.collector.update_device_status('av-1', '10.0.0.2', False, 'socket error')
        self.collector.telegram_notifier.send_device_offline_alert.assert_called_once()

    def test_collect_all_devices_passes_custom_port(self):
        self.collector.devices = [
            {'device_id': 'av-1', 'device_name': 'A', 'ip_address': '10.0.0.2', 'port': 4029}
        ]
        with patch.object(self.collector, 'collect_device_data') as collect:
            self.collector.collect_all_devices()
            collect.assert_called_once_with('av-1', '10.0.0.2', port=4029)

    def test_collect_all_devices_defaults_port_when_missing(self):
        self.collector.devices = [
            {'device_id': 'av-1', 'device_name': 'A', 'ip_address': '10.0.0.2'}
        ]
        with patch.object(self.collector, 'collect_device_data') as collect:
            self.collector.collect_all_devices()
            collect.assert_called_once_with('av-1', '10.0.0.2', port=4028)
