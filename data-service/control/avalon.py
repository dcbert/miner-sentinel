"""Avalon cgminer TCP control (ascset on :4028)."""

from __future__ import annotations

import json
import logging
import socket
from typing import Any

logger = logging.getLogger(__name__)


class AvalonControlAdapter:
    """Control surface for Avalon Nano / cgminer API."""

    MAKE = 'avalon'
    TIMEOUT = 10

    def __init__(self, ip_address: str, port: int | None = 4028):
        self.ip = ip_address
        self.port = int(port or 4028)

    def _socket_request(self, command: str, parameter: str | None = None) -> Any:
        """Send cgminer JSON command (+ optional parameter for ascset)."""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.TIMEOUT)
            sock.connect((self.ip, self.port))
            payload_obj: dict[str, Any] = {'command': command}
            if parameter is not None:
                payload_obj['parameter'] = parameter
            payload = json.dumps(payload_obj)
            sock.send(payload.encode('utf-8'))
            response = b''
            while True:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    response += data
                except socket.timeout:
                    break
            raw = response.decode('utf-8', errors='ignore').replace('\x00', '').strip()
            logger.info('Avalon control response from %s: %s...', self.ip, raw[:200])
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {'raw_response': raw}
        finally:
            if sock:
                sock.close()

    def _ascset(self, params: str) -> dict[str, Any]:
        # cgminer expects {"command":"ascset","parameter":"0,fan-spd,-1"}
        # (pipe-in-command form returns Invalid command on Avalon Nano3s)
        logger.info('Avalon ascset %s:%s -> %s', self.ip, self.port, params)
        parsed = self._socket_request('ascset', params)
        ok = self._is_success(parsed)
        return {'ok': ok, 'response': parsed, 'command': f'ascset|{params}'}

    @staticmethod
    def _is_success(parsed: Any) -> bool:
        if not isinstance(parsed, dict):
            return bool(parsed)
        status = parsed.get('STATUS')
        if isinstance(status, list) and status:
            entry = status[0]
            if isinstance(entry, dict):
                return str(entry.get('STATUS', '')).upper() in ('S', 'SUCCESS')
        if status == 'S':
            return True
        # Some firmwares only echo STATS/empty on success
        if 'STATUS' not in parsed and parsed:
            return True
        return False

    def reboot(self) -> dict[str, Any]:
        result = self._ascset('0,reboot,0')
        result['action'] = 'reboot'
        if not result['ok']:
            raise RuntimeError(f"Avalon reboot failed: {result.get('response')}")
        return result

    def set_fan(self, *, percent: int | None = None, auto: bool | None = None) -> dict[str, Any]:
        # Avalon: fan-spd 15–100, or -1 for auto
        if auto is True or percent is None and auto is not False:
            value = -1
        else:
            value = max(15, min(100, int(percent if percent is not None else 50)))
        result = self._ascset(f'0,fan-spd,{value}')
        result['action'] = 'fan'
        result['params'] = {'percent': value if value >= 0 else None, 'auto': value == -1}
        if not result['ok']:
            raise RuntimeError(f"Avalon fan set failed: {result.get('response')}")
        return result

    def set_frequency(self, mhz: float) -> dict[str, Any]:
        result = self._ascset(f'0,frequency,{int(mhz)}')
        result['action'] = 'frequency'
        result['params'] = {'mhz': float(mhz)}
        if not result['ok']:
            raise RuntimeError(f"Avalon frequency set failed: {result.get('response')}")
        return result

    def set_voltage(self, millivolts: int) -> dict[str, Any]:
        result = self._ascset(f'0,voltage,{int(millivolts)}')
        result['action'] = 'voltage'
        result['params'] = {'millivolts': int(millivolts)}
        if not result['ok']:
            raise RuntimeError(f"Avalon voltage set failed: {result.get('response')}")
        return result

    def set_workmode(self, mode: int) -> dict[str, Any]:
        """Avalon workmode: 0=Low, 1=Mid, 2=High."""
        mode_i = int(mode)
        if mode_i not in (0, 1, 2):
            raise ValueError('workmode must be 0 (Low), 1 (Mid), or 2 (High)')
        result = self._ascset(f'0,workmode,set,{mode_i}')
        result['action'] = 'workmode'
        result['params'] = {
            'mode': mode_i,
            'label': {0: 'Low', 1: 'Mid', 2: 'High'}[mode_i],
        }
        if not result['ok']:
            raise RuntimeError(f"Avalon workmode set failed: {result.get('response')}")
        return result
