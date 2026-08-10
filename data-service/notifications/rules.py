"""
Notification rule helpers for data-service collectors.

Rules are loaded from collector_settings.notification_rules and merged with
defaults so partial/missing JSON is always safe.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

DEFAULT_NOTIFICATION_RULES: Dict[str, Dict[str, Any]] = {
    'device_offline': {'enabled': True},
    'device_online': {'enabled': True},
    'hashrate_stagnation': {
        'enabled': True,
        'threshold_collections': 3,
        'tolerance_ghs': 0.1,
    },
    'auto_restart': {'enabled': True},
    'best_difficulty': {
        'enabled': True,
        'min_improvement_percent': 5.0,
    },
}


def merge_notification_rules(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Deep-merge stored rules with defaults."""
    merged: Dict[str, Dict[str, Any]] = {}
    stored = raw if isinstance(raw, dict) else {}
    for key, defaults in DEFAULT_NOTIFICATION_RULES.items():
        entry = deepcopy(defaults)
        user = stored.get(key)
        if isinstance(user, dict):
            if 'enabled' in user:
                entry['enabled'] = bool(user['enabled'])
            if key == 'hashrate_stagnation':
                try:
                    n = int(user.get('threshold_collections', entry['threshold_collections']))
                    entry['threshold_collections'] = max(2, min(20, n))
                except (TypeError, ValueError):
                    pass
                try:
                    t = float(user.get('tolerance_ghs', entry['tolerance_ghs']))
                    entry['tolerance_ghs'] = max(0.0, min(100.0, t))
                except (TypeError, ValueError):
                    pass
            if key == 'best_difficulty':
                try:
                    p = float(user.get('min_improvement_percent', entry['min_improvement_percent']))
                    entry['min_improvement_percent'] = max(0.0, min(100.0, p))
                except (TypeError, ValueError):
                    pass
        merged[key] = entry
    return merged


class NotificationRules:
    """Runtime accessor for alert enablement and thresholds."""

    def __init__(self, raw: Any = None):
        self._rules = merge_notification_rules(raw)

    def update(self, raw: Any) -> None:
        self._rules = merge_notification_rules(raw)

    def enabled(self, key: str) -> bool:
        entry = self._rules.get(key) or {}
        return bool(entry.get('enabled', True))

    def get(self, key: str, field: str, default=None):
        entry = self._rules.get(key) or {}
        return entry.get(field, default)

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        return deepcopy(self._rules)
