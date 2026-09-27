"""Unit tests for device control adapters (mocked network I/O)."""

from unittest.mock import MagicMock, patch

import pytest

from control.avalon import AvalonControlAdapter
from control.bitaxe import BitaxeControlAdapter
from control.capabilities import capabilities_for_make, event_type_for_action
from control.dispatcher import execute_control


class TestCapabilities:
    def test_bitaxe_has_pause_and_pool(self):
        caps = capabilities_for_make('bitaxe')
        assert caps['reboot'] is True
        assert caps['pause'] is True
        assert caps['set_pool'] is True
        assert caps['workmode'] is False

    def test_avalon_has_workmode_not_pause(self):
        caps = capabilities_for_make('avalon')
        assert caps['workmode'] is True
        assert caps['pause'] is False
        assert caps['set_pool'] is False
        assert caps['frequency'] is False
        assert caps['voltage'] is False

    def test_unknown_make_all_false(self):
        caps = capabilities_for_make('braiins')
        assert caps['reboot'] is False

    def test_event_types(self):
        assert event_type_for_action('reboot') == 'user_reboot'
        assert event_type_for_action('fan') == 'fan_changed'


class TestBitaxeAdapter:
    @patch('control.bitaxe.requests.post')
    def test_reboot(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
        adapter = BitaxeControlAdapter('192.168.1.7')
        result = adapter.reboot()
        assert result['ok'] is True
        mock_post.assert_called_once()
        assert '/api/system/restart' in mock_post.call_args[0][0]

    @patch('control.bitaxe.requests.patch')
    def test_set_fan_manual(self, mock_patch):
        mock_resp = MagicMock(status_code=200, content=b'{}')
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}
        mock_patch.return_value = mock_resp
        adapter = BitaxeControlAdapter('192.168.1.12')
        result = adapter.set_fan(percent=75, auto=False)
        assert result['ok'] is True
        body = mock_patch.call_args[1]['json']
        assert body['fanspeed'] == 75
        assert body['autofanspeed'] == 0

    @patch('control.bitaxe.requests.patch')
    def test_set_frequency_voltage(self, mock_patch):
        mock_resp = MagicMock(status_code=200, content=b'')
        mock_resp.raise_for_status = MagicMock()
        mock_patch.return_value = mock_resp
        adapter = BitaxeControlAdapter('192.168.1.7')
        adapter.set_frequency(500)
        assert mock_patch.call_args[1]['json']['frequency'] == 500.0
        adapter.set_voltage(1200)
        assert mock_patch.call_args[1]['json']['coreVoltage'] == 1200

    @patch('control.bitaxe.requests.post')
    def test_pause_unsupported(self, mock_post):
        mock_post.return_value = MagicMock(status_code=404)
        adapter = BitaxeControlAdapter('192.168.1.7')
        with pytest.raises(RuntimeError, match='pause not supported'):
            adapter.pause()


class TestAvalonAdapter:
    @patch.object(AvalonControlAdapter, '_socket_request')
    def test_reboot_ascset(self, mock_sock):
        mock_sock.return_value = {'STATUS': [{'STATUS': 'S'}]}
        adapter = AvalonControlAdapter('192.168.1.11', 4028)
        result = adapter.reboot()
        assert result['ok'] is True
        mock_sock.assert_called_once_with('ascset', '0,reboot,0')

    @patch.object(AvalonControlAdapter, '_socket_request')
    def test_fan_auto(self, mock_sock):
        mock_sock.return_value = {'STATUS': [{'STATUS': 'S'}]}
        adapter = AvalonControlAdapter('192.168.1.11')
        result = adapter.set_fan(auto=True)
        assert result['params']['auto'] is True
        mock_sock.assert_called_once_with('ascset', '0,fan-spd,-1')

    @patch.object(AvalonControlAdapter, '_socket_request')
    def test_workmode(self, mock_sock):
        mock_sock.return_value = {'STATUS': [{'STATUS': 'S'}]}
        adapter = AvalonControlAdapter('192.168.1.11')
        result = adapter.set_workmode(2)
        assert result['params']['label'] == 'High'
        mock_sock.assert_called_once_with('ascset', '0,workmode,set,2')

    def test_workmode_invalid(self):
        adapter = AvalonControlAdapter('192.168.1.11')
        with pytest.raises(ValueError):
            adapter.set_workmode(9)


class TestDispatcher:
    @patch('control.dispatcher.BitaxeControlAdapter')
    def test_execute_bitaxe_reboot(self, mock_cls):
        instance = mock_cls.return_value
        instance.reboot.return_value = {'ok': True, 'action': 'reboot'}
        result = execute_control(
            make='bitaxe',
            ip_address='192.168.1.7',
            port=80,
            action='reboot',
            params={},
        )
        assert result['event_type'] == 'user_reboot'
        instance.reboot.assert_called_once()

    def test_unsupported_action(self):
        with pytest.raises(ValueError, match='not supported'):
            execute_control(
                make='avalon',
                ip_address='192.168.1.11',
                port=4028,
                action='pause',
                params={},
            )

    @patch('control.dispatcher.AvalonControlAdapter')
    def test_avalon_workmode_label(self, mock_cls):
        instance = mock_cls.return_value
        instance.set_workmode.return_value = {'ok': True, 'action': 'workmode'}
        execute_control(
            make='avalon',
            ip_address='192.168.1.11',
            port=4028,
            action='workmode',
            params={'mode': 'high'},
        )
        instance.set_workmode.assert_called_once_with(2)
