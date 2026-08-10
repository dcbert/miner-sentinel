"""
Avalon API serializers — thin re-exports of unified serializers.

Kept so older imports continue to work after Release C.
"""

from .serializers import AvalonDeviceWriteSerializer
from .unified_serializers import (
    UnifiedDeviceAsAvalonSerializer as AvalonDeviceSerializer,
    UnifiedHardwareSerializer as AvalonHardwareLogsSerializer,
    UnifiedMiningAsAvalonSerializer as AvalonMiningStatsSerializer,
    UnifiedSystemAsAvalonSerializer as AvalonSystemInfoSerializer,
)

__all__ = [
    'AvalonDeviceSerializer',
    'AvalonDeviceWriteSerializer',
    'AvalonMiningStatsSerializer',
    'AvalonHardwareLogsSerializer',
    'AvalonSystemInfoSerializer',
]
