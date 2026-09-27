"""Device control adapters (MinerWatch-style actions)."""

from control.capabilities import CAPABILITIES_BY_MAKE, capabilities_for_make
from control.dispatcher import execute_control

__all__ = [
    'CAPABILITIES_BY_MAKE',
    'capabilities_for_make',
    'execute_control',
]
