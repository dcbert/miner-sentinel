"""Unit tests for normalize paths (Bitaxe, Avalon, CKPool, PublicPool)."""
import sys
from pathlib import Path

import pytest

# Ensure data-service root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.avalon_collector import AvalonCollector
from collectors.bitaxe_collector import BitAxeCollector
from collectors.ckpool_collector import CKPoolCollector
from collectors.normalized import efficiency_j_per_th
from collectors.publicpool_collector import PublicPoolCollector


def test_efficiency_j_per_th():
    assert efficiency_j_per_th(20.0, 500.0) == pytest.approx(40.0)
    assert efficiency_j_per_th(20.0, 0) == 0.0


class TestBitaxeNormalize:
    def setup_method(self):
        self.collector = BitAxeCollector('postgresql://u:p@localhost/db', dual_write=False)

    def test_hashrate_units_passthrough(self):
        snap = self.collector.normalize_system_info(
            {'hashRate': 512.25, 'power': 0, 'voltage': 0},
            'bx-1',
        )
        assert snap.mining.hashrate_ghs == pytest.approx(512.25)

    def test_difficulty_suffixes(self):
        snap = self.collector.normalize_system_info(
            {
                'hashRate': 1,
                'bestDiff': '22.3 M',
                'bestSessionDiff': '1.5 K',
                'power': 10,
                'voltage': 1200,
            },
            'bx-1',
        )
        assert snap.mining.best_difficulty == pytest.approx(22.3e6)
        assert snap.mining.best_session_difficulty == pytest.approx(1500.0)

    def test_efficiency_and_voltage(self):
        snap = self.collector.normalize_system_info(
            {'hashRate': 500, 'power': 20, 'voltage': 1200, 'temp': 55, 'fanrpm': 2000},
            'bx-1',
        )
        assert snap.hardware.efficiency_j_per_th == pytest.approx(40.0)
        assert snap.hardware.voltage == pytest.approx(1.2)
        assert snap.hardware.temperature_c == 55

    def test_system_details_keys(self):
        snap = self.collector.normalize_system_info(
            {
                'hashRate': 1,
                'ASICModel': 'BM1366',
                'boardVersion': '401',
                'freeHeap': 999,
                'version': 'v2',
                'hostname': 'axe',
                'macAddr': 'aa:bb',
            },
            'bx-1',
        )
        assert snap.system.model_reported == 'BM1366'
        assert snap.system.details['asic_model'] == 'BM1366'
        assert snap.system.details['free_heap'] == 999
        assert snap.system.firmware_version == 'v2'


class TestAvalonNormalize:
    def setup_method(self):
        self.collector = AvalonCollector('postgresql://u:p@localhost/db', dual_write=False)

    def test_mhs_to_ghs(self):
        assert self.collector._parse_hashrate_mhs('4500') == pytest.approx(4.5)

    def test_full_normalize_best_share(self):
        summary = {
            'MHS 5s': '4500',
            'Elapsed': 100,
            'Accepted': 10,
            'Rejected': 1,
            'Found Blocks': 0,
            'Best Share': 12345.6,
        }
        stats = {'MM ID0': 'OTemp[62],MPO[80],Fan1[1500],Freq[464.89],PVT_V0[300]'}
        version = {'MODEL': 'Nano3s', 'CGMiner': '4.11', 'MAC': 'aa', 'DNA': 'x', 'HWTYPE': 'hw'}
        pools = {'URL': 'stratum+tcp://pool', 'User': 'worker'}
        snap = self.collector.normalize_responses(
            'av-1', '10.0.0.1', 'Avalon', version, summary, stats, pools
        )
        assert snap.mining.hashrate_ghs == pytest.approx(4.5)
        assert snap.mining.best_difficulty == pytest.approx(12345.6)
        assert snap.mining.best_session_difficulty is None
        assert snap.hardware.temperature_c == pytest.approx(62.0)
        assert snap.hardware.power_watts == pytest.approx(80.0)
        assert snap.system.model_reported == 'Nano3s'

    def test_power_prefers_mpo(self):
        stats = {'MM ID0': 'MPO[100],PS[1 2 3 4 5 6 999]'}
        assert self.collector._parse_power_from_stats(stats) == pytest.approx(100.0)


class TestCKPoolNormalize:
    def setup_method(self):
        self.collector = CKPoolCollector(None, pool_url='https://eusolo.ckpool.org', pool_address='bc1q')

    def test_string_hashrates(self):
        snap = self.collector.normalize_stats({
            'hashrate1m': '466G',
            'hashrate5m': '450G',
            'hashrate1hr': '400G',
            'hashrate1d': '1.29T',
            'hashrate7d': '1T',
            'workers': 2,
            'shares': 100,
            'bestshare': 1e12,
            'bestever': 2e12,
            'lastshare': 1700000000,
            'authorised': 1600000000,
        })
        assert snap.pool_type == 'ckpool'
        assert snap.hashrate_1m_ghs == pytest.approx(466.0)
        assert snap.hashrate_1d_ghs == pytest.approx(1290.0)
        assert snap.hashrate_1m_display == '466G'
        assert snap.workers == 2


class TestPublicPoolNormalize:
    def setup_method(self):
        self.collector = PublicPoolCollector(None, pool_url='http://localhost:3334', pool_address='bc1q')

    def test_hs_to_ghs_and_null_windows(self):
        client = {
            'workersCount': 1,
            'workers': [{'hashRate': 500_000_000_000}],  # 500 GH/s in H/s
            'bestDifficulty': 1e9,
        }
        pool = {'totalHashRate': 1_000_000_000_000, 'totalMiners': 50}
        snap = self.collector.normalize_stats(client, pool)
        assert snap.pool_type == 'publicpool'
        assert snap.hashrate_1m_ghs == pytest.approx(500.0)
        assert snap.hashrate_5m_ghs is None
        assert snap.hashrate_1d_ghs is None
        assert snap.workers == 1
        assert snap.details.get('workers')
        assert snap.pool_total_miners == 50
