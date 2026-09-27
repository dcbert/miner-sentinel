"""Capability map: which control actions each miner make supports."""

# Actions shared across makes that expose write APIs.
# Frontend uses this list to gate Controls UI (never show unsupported buttons).

CAPABILITIES_BY_MAKE = {
    'bitaxe': {
        'reboot': True,
        'fan': True,
        'frequency': True,
        'voltage': True,
        'pause': True,
        'resume': True,
        'set_pool': True,
        'workmode': False,
    },
    'avalon': {
        'reboot': True,
        'fan': True,
        # Home Avalon Nano/Mini cgminer does not reliably expose freq/voltage writes
        'frequency': False,
        'voltage': False,
        'pause': False,
        'resume': False,
        'set_pool': False,  # write path not verified for home Avalon cgminer
        'workmode': True,
    },
    'nmaxe': {
        'reboot': True,
        'fan': True,
        'frequency': True,
        'voltage': True,
        'pause': False,
        'resume': False,
        'set_pool': True,
        'workmode': False,
    },
    'nerdnos': {
        'reboot': False,
        'fan': False,
        'frequency': False,
        'voltage': False,
        'pause': False,
        'resume': False,
        'set_pool': False,
        'workmode': False,
    },
}

# Human labels for Activity / AlertEvent rows
ACTION_EVENT_TYPES = {
    'reboot': 'user_reboot',
    'fan': 'fan_changed',
    'frequency': 'frequency_changed',
    'voltage': 'voltage_changed',
    'pause': 'mining_paused',
    'resume': 'mining_resumed',
    'set_pool': 'pool_changed',
    'workmode': 'workmode_changed',
}


def capabilities_for_make(make: str) -> dict:
    base = CAPABILITIES_BY_MAKE.get((make or '').lower(), {})
    if not base:
        return {
            'reboot': False,
            'fan': False,
            'frequency': False,
            'voltage': False,
            'pause': False,
            'resume': False,
            'set_pool': False,
            'workmode': False,
        }
    return dict(base)


def event_type_for_action(action: str) -> str:
    return ACTION_EVENT_TYPES.get(action, f'control_{action}')
