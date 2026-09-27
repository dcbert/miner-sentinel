"""Bitaxe / NerdQAxe / NMAxe AxeOS-style HTTP control."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class BitaxeControlAdapter:
    """Control surface for AxeOS HTTP API (Bitaxe, NerdQAxe, similar forks)."""

    MAKE = 'bitaxe'
    TIMEOUT = 10

    def __init__(self, ip_address: str, port: int | None = None):
        host = ip_address
        if port and int(port) not in (80, 0):
            host = f'{ip_address}:{int(port)}'
        self.base = f'http://{host}'

    def _url(self, path: str) -> str:
        return f'{self.base}{path}'

    def reboot(self) -> dict[str, Any]:
        url = self._url('/api/system/restart')
        logger.info('Bitaxe reboot POST %s', url)
        resp = requests.post(url, timeout=self.TIMEOUT)
        resp.raise_for_status()
        return {'ok': True, 'action': 'reboot'}

    def set_fan(self, *, percent: int | None = None, auto: bool | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if auto is True:
            body['autofanspeed'] = 1
        elif auto is False or percent is not None:
            body['autofanspeed'] = 0
            if percent is not None:
                pct = max(0, min(100, int(percent)))
                body['fanspeed'] = pct
        if not body:
            raise ValueError('fan requires percent and/or auto')
        return self._patch_system(body, action='fan')

    def set_frequency(self, mhz: float) -> dict[str, Any]:
        return self._patch_system({'frequency': float(mhz)}, action='frequency')

    def set_voltage(self, millivolts: int) -> dict[str, Any]:
        # AxeOS expects coreVoltage in mV
        return self._patch_system({'coreVoltage': int(millivolts)}, action='voltage')

    def pause(self) -> dict[str, Any]:
        url = self._url('/api/system/pause')
        logger.info('Bitaxe pause POST %s', url)
        resp = requests.post(url, timeout=self.TIMEOUT)
        # Some firmware returns 404 if unsupported — surface clearly
        if resp.status_code == 404:
            raise RuntimeError('pause not supported by this firmware')
        resp.raise_for_status()
        return {'ok': True, 'action': 'pause'}

    def resume(self) -> dict[str, Any]:
        url = self._url('/api/system/resume')
        logger.info('Bitaxe resume POST %s', url)
        resp = requests.post(url, timeout=self.TIMEOUT)
        if resp.status_code == 404:
            raise RuntimeError('resume not supported by this firmware')
        resp.raise_for_status()
        return {'ok': True, 'action': 'resume'}

    def set_pool(
        self,
        *,
        stratum_url: str,
        stratum_user: str,
        stratum_password: str | None = None,
        restart: bool = True,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            'stratumURL': stratum_url,
            'stratumUser': stratum_user,
        }
        if stratum_password is not None:
            body['stratumPassword'] = stratum_password
        result = self._patch_system(body, action='set_pool')
        if restart:
            try:
                self.reboot()
                result['restarted'] = True
            except Exception as exc:  # noqa: BLE001 — pool set may still succeed
                logger.warning('Pool set OK but restart failed: %s', exc)
                result['restarted'] = False
                result['restart_error'] = str(exc)
        return result

    def _patch_system(self, body: dict[str, Any], action: str) -> dict[str, Any]:
        url = self._url('/api/system')
        logger.info('Bitaxe PATCH %s body=%s', url, {k: ('***' if 'pass' in k.lower() else v) for k, v in body.items()})
        resp = requests.patch(url, json=body, timeout=self.TIMEOUT)
        resp.raise_for_status()
        out: dict[str, Any] = {'ok': True, 'action': action, 'params': body}
        try:
            if resp.content:
                out['response'] = resp.json()
        except Exception:  # noqa: BLE001
            pass
        return out
