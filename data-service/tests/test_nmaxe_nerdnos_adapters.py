"""Adapter unit tests for NMAxe (#14) and NerdNOS (#25)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.nerdnos_collector import NerdNOSCollector
from collectors.nmaxe_collector import NMAxeCollector
from collectors.normalized import parse_difficulty


def test_parse_difficulty_suffixes():
    assert parse_difficulty('20.64G') == pytest.approx(20.64e9)
    assert parse_difficulty('2.251M') == pytest.approx(2.251e6)
    assert parse_difficulty('1.036K') == pytest.approx(1036.0)
    assert parse_difficulty(23196269) == pytest.approx(23196269)
    assert parse_difficulty(None) == 0.0


class TestNMAxeNormalize:
    def setup_method(self):
        self.collector = NMAxeCollector('postgresql://u:p@localhost/db')

    def test_nested_v3_payload(self):
        payload = {
            'power': {'power': 23.15920639, 'vbus': 11431, 'ibus': 2026},
            'temps': {'vcore': 49.5, 'asic': 50.13000107},
            'asic': {
                'count': 1,
                'model': 'BM1370',
                'vcoreReq': 1126,
                'vcoreReal': 1124,
                'freqReq': 600,
                'smallCoreCnt': 2040,
            },
            'miner': {
                'hashRate': 1417.14832,
                'bestDiffEver': '20.64G',
                'bestDiffSession': '2.251M',
                'networkDiff': '132.5T',
                'poolDiff': '1.036K',
                'lastDiff': '2.084K',
                'blkhits': 0,
                'freeHeap': 109860,
                'sAccepted': 3978,
                'sRejected': 0,
                'uptimeSeconds': 12208,
                'uptimeEver': 12361940,
            },
            'identity': {
                'fwVersion': 'v3.0.12',
                'hwModel': 'NMAxeGamma',
                'hostName': 'nmaxeg2',
                'ssid': 'HomeNet',
                'rssi': -56,
                'appSha256': 'e8e146a2051dc85c',
                'displayName': 'Gamma living room',
            },
            'stratum': {
                'url': 'stratum+tcp://pool.example:3456',
                'user': 'bc1qworker.nmaxeg2',
                'pwd': 'x',
            },
            'fans': [{'id': 0, 'speed': 100, 'rpm': 6886}],
        }
        snap = self.collector.normalize_system_info(payload, 'nmaxeg2')
        assert snap.make == 'nmaxe'
        assert snap.online is True
        assert snap.mining.hashrate_ghs == pytest.approx(1417.14832)
        assert snap.mining.best_difficulty == pytest.approx(20.64e9)
        assert snap.mining.best_session_difficulty == pytest.approx(2.251e6)
        assert snap.mining.shares_accepted == 3978
        assert snap.mining.shares_rejected == 0
        assert snap.mining.uptime_seconds == 12208
        assert snap.mining.pool_url.startswith('stratum+tcp://')
        assert snap.hardware.temperature_c == pytest.approx(50.13000107)
        assert snap.hardware.power_watts == pytest.approx(23.15920639)
        assert snap.hardware.fan_speed_rpm == 6886
        assert snap.hardware.fan_speed_percent == 100
        assert snap.hardware.voltage == pytest.approx(1.124)
        assert snap.hardware.frequency_mhz == pytest.approx(600.0)
        assert snap.system.hostname == 'nmaxeg2'
        assert snap.system.firmware_version == 'v3.0.12'
        assert snap.system.model_reported == 'NMAxeGamma'
        assert snap.system.details['api_shape'] == 'nmaxe_nested'
        assert snap.system.details['asic_model'] == 'BM1370'
        assert snap.system.details['display_name'] == 'Gamma living room'
        # Never pass nested dicts as top-level metric values
        assert not isinstance(snap.mining.hashrate_ghs, dict)
        assert not isinstance(snap.hardware.power_watts, dict)

    def test_nested_does_not_treat_power_object_as_float(self):
        """Regression: nested power dict must not reach DB as non-numeric."""
        payload = {
            'power': {'power': 10.0},
            'temps': {'asic': 40.0},
            'miner': {'hashRate': 100.0, 'sAccepted': 1, 'sRejected': 0, 'uptimeSeconds': 1},
            'identity': {'fwVersion': 'v3.0.20', 'hwModel': 'NMAxeGamma', 'hostName': 'n'},
            'stratum': {},
            'fans': [],
            'asic': {},
        }
        snap = self.collector.normalize_system_info(payload, 'n')
        assert isinstance(snap.hardware.power_watts, float)
        assert snap.hardware.power_watts == pytest.approx(10.0)


class TestNerdNOSNormalize:
    def setup_method(self):
        self.collector = NerdNOSCollector('postgresql://u:p@localhost/db')

    def test_status_payload_issue_25(self):
        payload = {
            'hashrate_ghs': 196.56,
            'temperature_c': 58.9,
            'hostname': 'NerdNOS',
            'bestDifficulty': 23196269,
            'shares_a': 3766,
            'mac': 'AA:BB:CC:DD:EE:FF',
            'firmware_version': '2.0.5',
        }
        snap = self.collector.normalize_status(payload, 'nerd-1')
        assert snap.make == 'nerdnos'
        assert snap.mining.hashrate_ghs == pytest.approx(196.56)
        assert snap.hardware.temperature_c == pytest.approx(58.9)
        assert snap.mining.best_difficulty == pytest.approx(23196269)
        assert snap.mining.shares_accepted == 3766
        assert snap.system.hostname == 'NerdNOS'
        assert snap.system.mac_address == 'AA:BB:CC:DD:EE:FF'
        assert snap.system.firmware_version == '2.0.5'
        assert snap.system.model_reported == 'NerdNOS'
        assert snap.system.details['api_shape'] == 'nerdnos_status'

    def test_status_aliases(self):
        payload = {
            'hashRate': 50.0,
            'temp': 45.0,
            'bestDiff': '1.5M',
            'sharesAccepted': 10,
            'sharesRejected': 1,
            'hostName': 'nn',
            'macAddr': '11:22',
            'version': '1.0',
        }
        snap = self.collector.normalize_status(payload, 'nerd-2')
        assert snap.mining.hashrate_ghs == pytest.approx(50.0)
        assert snap.hardware.temperature_c == pytest.approx(45.0)
        assert snap.mining.best_difficulty == pytest.approx(1.5e6)
        assert snap.mining.shares_accepted == 10
        assert snap.mining.shares_rejected == 1
