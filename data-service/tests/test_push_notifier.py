"""Unit tests for ntfy / Gotify / webhook PushNotifier."""
from unittest.mock import MagicMock, patch

from notifications.push_notifier import PushNotifier, push_notifier_from_settings


class TestPushNotifier:
    def test_disabled_without_config(self):
        n = PushNotifier()
        assert n.enabled is False
        assert n.deliver(title='t', message='m') is False

    def test_ntfy_enabled_with_url(self):
        n = PushNotifier(ntfy_enabled=True, ntfy_url='https://ntfy.sh/topic')
        assert n.enabled is True
        assert n.ntfy_enabled is True

    @patch('notifications.push_notifier.requests.post')
    def test_deliver_ntfy(self, mock_post):
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        n = PushNotifier(ntfy_enabled=True, ntfy_url='https://ntfy.sh/lab', ntfy_token='tok')
        assert n.deliver(title='Offline', message='Bitaxe down', severity='critical') is True
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://ntfy.sh/lab'
        assert kwargs['headers']['Title'] == 'Offline'
        assert kwargs['headers']['Priority'] == '5'
        assert kwargs['headers']['Authorization'] == 'Bearer tok'

    @patch('notifications.push_notifier.requests.post')
    def test_deliver_gotify(self, mock_post):
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        n = PushNotifier(
            gotify_enabled=True,
            gotify_url='https://gotify.home/',
            gotify_token='app-token',
        )
        assert n.deliver(title='Test', message='Hello', severity='info') is True
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://gotify.home/message'
        assert kwargs['params']['token'] == 'app-token'
        assert kwargs['json']['title'] == 'Test'
        assert kwargs['json']['priority'] == 3

    @patch('notifications.push_notifier.requests.post')
    def test_deliver_webhook(self, mock_post):
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        n = PushNotifier(webhook_enabled=True, webhook_url='https://hooks.example/x')
        assert n.deliver(title='T', message='M', severity='warn', event_key='device_offline') is True
        payload = mock_post.call_args[1]['json']
        assert payload['source'] == 'minersentinel'
        assert payload['event_key'] == 'device_offline'

    def test_from_settings(self):
        n = push_notifier_from_settings({
            'ntfy_enabled': True,
            'ntfy_url': 'https://ntfy.sh/x',
            'gotify_enabled': False,
            'webhook_enabled': False,
        })
        assert n.enabled is True
        assert n.ntfy_enabled is True
