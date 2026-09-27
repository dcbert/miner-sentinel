"""
ntfy / Gotify / generic webhook fan-out for MinerSentinel alerts.

Self-hosters on Umbrel often prefer these over Discord. Web Push (VAPID)
remains optional/deferred — ship working ntfy first.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SEVERITY_PRIORITY = {
    'info': 3,
    'warn': 4,
    'critical': 5,
}


class PushNotifier:
    """Delivers plain-text alerts to ntfy, Gotify, and/or a generic webhook."""

    def __init__(
        self,
        *,
        ntfy_enabled: bool = False,
        ntfy_url: Optional[str] = None,
        ntfy_token: Optional[str] = None,
        gotify_enabled: bool = False,
        gotify_url: Optional[str] = None,
        gotify_token: Optional[str] = None,
        webhook_enabled: bool = False,
        webhook_url: Optional[str] = None,
    ):
        self.ntfy_url = (ntfy_url or os.getenv('NTFY_URL') or '').strip()
        self.ntfy_token = (ntfy_token or os.getenv('NTFY_TOKEN') or '').strip()
        self.gotify_url = (gotify_url or os.getenv('GOTIFY_URL') or '').strip().rstrip('/')
        self.gotify_token = (gotify_token or os.getenv('GOTIFY_TOKEN') or '').strip()
        self.webhook_url = (webhook_url or os.getenv('ALERT_WEBHOOK_URL') or '').strip()

        self.ntfy_enabled = bool(ntfy_enabled and self.ntfy_url)
        self.gotify_enabled = bool(gotify_enabled and self.gotify_url and self.gotify_token)
        self.webhook_enabled = bool(webhook_enabled and self.webhook_url)
        self.enabled = self.ntfy_enabled or self.gotify_enabled or self.webhook_enabled

        if self.enabled:
            channels = []
            if self.ntfy_enabled:
                channels.append('ntfy')
            if self.gotify_enabled:
                channels.append('gotify')
            if self.webhook_enabled:
                channels.append('webhook')
            logger.info(f"Push notifier enabled: {', '.join(channels)}")
        else:
            logger.debug("Push notifier disabled (no ntfy/Gotify/webhook configured)")

    def deliver(
        self,
        *,
        title: str,
        message: str,
        severity: str = 'warn',
        event_key: str = '',
    ) -> bool:
        if not self.enabled:
            return False
        ok = False
        if self.ntfy_enabled:
            ok = self._send_ntfy(title, message, severity) or ok
        if self.gotify_enabled:
            ok = self._send_gotify(title, message, severity) or ok
        if self.webhook_enabled:
            ok = self._send_webhook(title, message, severity, event_key) or ok
        return ok

    def _send_ntfy(self, title: str, message: str, severity: str) -> bool:
        headers = {
            'Title': (title or 'MinerSentinel')[:250],
            'Priority': str(SEVERITY_PRIORITY.get(severity, 4)),
            'Tags': 'pick,mining',
        }
        if self.ntfy_token:
            headers['Authorization'] = f'Bearer {self.ntfy_token}'
        try:
            resp = requests.post(
                self.ntfy_url,
                data=(message or title or '').encode('utf-8'),
                headers=headers,
                timeout=10,
            )
            if resp.ok:
                logger.info(f"ntfy message sent ({resp.status_code})")
                return True
            logger.error(f"ntfy error: {resp.status_code} - {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"ntfy send failed: {e}")
            return False

    def _send_gotify(self, title: str, message: str, severity: str) -> bool:
        priority = SEVERITY_PRIORITY.get(severity, 4)
        try:
            resp = requests.post(
                f'{self.gotify_url}/message',
                params={'token': self.gotify_token},
                json={
                    'title': title or 'MinerSentinel',
                    'message': message or title or '',
                    'priority': priority,
                },
                timeout=10,
            )
            if resp.ok:
                logger.info(f"Gotify message sent ({resp.status_code})")
                return True
            logger.error(f"Gotify error: {resp.status_code} - {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Gotify send failed: {e}")
            return False

    def _send_webhook(self, title: str, message: str, severity: str, event_key: str) -> bool:
        payload = {
            'source': 'minersentinel',
            'title': title or 'MinerSentinel',
            'message': message or title or '',
            'severity': severity,
            'event_key': event_key or '',
        }
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.ok:
                logger.info(f"Webhook delivered ({resp.status_code})")
                return True
            logger.error(f"Webhook error: {resp.status_code} - {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False

    def test_connection(self) -> bool:
        return self.deliver(
            title='MinerSentinel test',
            message='Push notifications (ntfy / Gotify / webhook) are working correctly.',
            severity='info',
            event_key='test',
        )


def push_notifier_from_settings(settings: dict) -> PushNotifier:
    """Build a PushNotifier from collector_settings row/dict."""
    return PushNotifier(
        ntfy_enabled=bool(settings.get('ntfy_enabled')),
        ntfy_url=settings.get('ntfy_url') or '',
        ntfy_token=settings.get('ntfy_token') or '',
        gotify_enabled=bool(settings.get('gotify_enabled')),
        gotify_url=settings.get('gotify_url') or '',
        gotify_token=settings.get('gotify_token') or '',
        webhook_enabled=bool(settings.get('webhook_enabled')),
        webhook_url=settings.get('webhook_url') or '',
    )
