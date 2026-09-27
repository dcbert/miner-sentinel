"""Dispatch control actions to make-specific adapters."""

from __future__ import annotations

import logging
from typing import Any

from control.avalon import AvalonControlAdapter
from control.bitaxe import BitaxeControlAdapter
from control.capabilities import capabilities_for_make, event_type_for_action

logger = logging.getLogger(__name__)

VALID_ACTIONS = frozenset({
    'reboot', 'fan', 'frequency', 'voltage', 'pause', 'resume', 'set_pool', 'workmode',
})


def execute_control(
    *,
    make: str,
    ip_address: str,
    port: int | None,
    action: str,
    params: dict | None = None,
) -> dict[str, Any]:
    """
    Run a control action against a device.

    Returns a result dict with ok/action/event_type and adapter-specific fields.
    Raises ValueError for unsupported/invalid requests; RuntimeError for device failures.
    """
    make_l = (make or '').lower()
    action_l = (action or '').lower().strip()
    params = params or {}

    if action_l not in VALID_ACTIONS:
        raise ValueError(f'Unknown action: {action}')

    caps = capabilities_for_make(make_l)
    if not caps.get(action_l):
        raise ValueError(f'Action "{action_l}" is not supported for make "{make_l}"')

    if make_l in ('bitaxe', 'nmaxe'):
        adapter = BitaxeControlAdapter(ip_address, port)
        result = _run_bitaxe(adapter, action_l, params)
    elif make_l == 'avalon':
        adapter = AvalonControlAdapter(ip_address, port)
        result = _run_avalon(adapter, action_l, params)
    else:
        raise ValueError(f'No control adapter for make "{make_l}"')

    result['event_type'] = event_type_for_action(action_l)
    result['make'] = make_l
    result['ip_address'] = ip_address
    return result


def _run_bitaxe(adapter: BitaxeControlAdapter, action: str, params: dict) -> dict[str, Any]:
    if action == 'reboot':
        return adapter.reboot()
    if action == 'fan':
        return adapter.set_fan(
            percent=params.get('percent', params.get('fanspeed')),
            auto=params.get('auto', params.get('autofan')),
        )
    if action == 'frequency':
        mhz = params.get('mhz', params.get('frequency'))
        if mhz is None:
            raise ValueError('frequency requires mhz')
        return adapter.set_frequency(float(mhz))
    if action == 'voltage':
        mv = params.get('millivolts', params.get('coreVoltage', params.get('voltage')))
        if mv is None:
            raise ValueError('voltage requires millivolts')
        # Accept volts if value looks like volts (< 20)
        mv_f = float(mv)
        if mv_f < 20:
            mv_f *= 1000
        return adapter.set_voltage(int(mv_f))
    if action == 'pause':
        return adapter.pause()
    if action == 'resume':
        return adapter.resume()
    if action == 'set_pool':
        url = params.get('stratum_url') or params.get('stratumURL') or params.get('url')
        user = params.get('stratum_user') or params.get('stratumUser') or params.get('user')
        if not url or not user:
            raise ValueError('set_pool requires stratum_url and stratum_user')
        password = params.get('stratum_password', params.get('stratumPassword', params.get('password')))
        restart = params.get('restart', True)
        return adapter.set_pool(
            stratum_url=str(url),
            stratum_user=str(user),
            stratum_password=None if password is None else str(password),
            restart=bool(restart),
        )
    raise ValueError(f'Unhandled bitaxe action: {action}')


def _run_avalon(adapter: AvalonControlAdapter, action: str, params: dict) -> dict[str, Any]:
    if action == 'reboot':
        return adapter.reboot()
    if action == 'fan':
        return adapter.set_fan(
            percent=params.get('percent', params.get('fanspeed')),
            auto=params.get('auto', params.get('autofan')),
        )
    if action == 'frequency':
        mhz = params.get('mhz', params.get('frequency'))
        if mhz is None:
            raise ValueError('frequency requires mhz')
        return adapter.set_frequency(float(mhz))
    if action == 'voltage':
        mv = params.get('millivolts', params.get('voltage'))
        if mv is None:
            raise ValueError('voltage requires millivolts')
        mv_f = float(mv)
        if mv_f < 20:
            mv_f *= 1000
        return adapter.set_voltage(int(mv_f))
    if action == 'workmode':
        mode = params.get('mode', params.get('workmode'))
        if mode is None:
            raise ValueError('workmode requires mode (0|1|2)')
        # Allow string labels
        if isinstance(mode, str):
            labels = {'low': 0, 'mid': 1, 'medium': 1, 'high': 2}
            mode = labels.get(mode.lower(), mode)
        return adapter.set_workmode(int(mode))
    raise ValueError(f'Unhandled avalon action: {action}')
