import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.parasite_collector import ParasiteCollector


ADDRESS = 'bc1qexampleaddress0000000000000000000000000'
API = 'https://parasite.space/api'


def sample_user(**overrides):
    payload = {
        'hashrate': 500_000_000_000,  # 500 GH/s in H/s (from upstream 5m)
        'workers': 2,
        'lastSubmission': '3m ago',
        'bestDifficulty': '1.5M',
        'uptime': '12d 4h',
        'workerData': [
            {
                'id': f'{ADDRESS}.bitaxe1',
                'name': 'bitaxe1',
                'hashrate': '250000000000',
                'bestDifficulty': '1500000',
                'lastSubmission': '1700000000',
                'uptime': 'N/A',
            }
        ],
    }
    payload.update(overrides)
    return payload


def sample_pool(**overrides):
    payload = {
        'uptime': '524d 17h',
        'lastBlockTime': '958527',
        'lastBlockHash': '00000000000000000000deadbeef',
        'highestDifficulty': '63.3T',
        'hashrate': 39_830_000_000_000_000,  # H/s
        'users': 2326,
        'workers': 4889,
        'workSinceLastBlock': 272954865012439,
    }
    payload.update(overrides)
    return payload


class TestParasiteNormalize:
    def setup_method(self):
        self.collector = ParasiteCollector(None, pool_address=ADDRESS)

    def test_normalize_maps_5m_and_pool_totals(self):
        snap = self.collector.normalize_stats(sample_user(), sample_pool())
        assert snap.pool_type == 'parasite'
        assert snap.pool_url == API
        assert snap.hashrate_1m_ghs == pytest.approx(500.0)
        assert snap.hashrate_5m_ghs == pytest.approx(500.0)
        assert snap.hashrate_1h_ghs is None
        assert snap.hashrate_1d_ghs is None
        assert snap.hashrate_7d_ghs is None
        assert snap.hashrate_1m_display == '500.00G'
        assert snap.hashrate_5m_display == '500.00G'
        assert snap.details['hashrate_windows']['1m'] == 'live'
        assert snap.details['hashrate_windows']['1h'] is None
        assert snap.last_share_unix == 1700000000
        assert snap.workers == 2
        assert snap.best_share == pytest.approx(1.5e6)
        assert snap.best_ever == pytest.approx(1.5e6)
        assert snap.shares is None
        assert snap.pool_total_miners == 2326
        assert snap.pool_total_hashrate_ghs == pytest.approx(39_830_000.0)
        assert snap.details['source'] == 'parasite'
        assert snap.details['uptime'] == '12d 4h'
        assert len(snap.details['workers']) == 1
        assert snap.details['pool_highest_difficulty'] == '63.3T'

    def test_missing_hashrate_stays_none(self):
        snap = self.collector.normalize_stats(sample_user(hashrate=None))
        assert snap.hashrate_5m_ghs is None
        assert snap.hashrate_5m_display is None
        assert snap.pool_total_miners is None

    def test_parse_difficulty_si_suffixes(self):
        assert ParasiteCollector.parse_difficulty('63.3T') == pytest.approx(63.3e12)
        assert ParasiteCollector.parse_difficulty('1.5M') == pytest.approx(1.5e6)
        assert ParasiteCollector.parse_difficulty(12345) == pytest.approx(12345.0)
        assert ParasiteCollector.parse_difficulty('??') is None
        assert ParasiteCollector.parse_difficulty(None) is None

    def test_normalize_base_url_appends_api(self):
        c = ParasiteCollector(None, pool_url='https://parasite.space', pool_address=ADDRESS)
        assert c.pool_url == 'https://parasite.space/api'


class TestParasiteFetch:
    def setup_method(self):
        self.collector = ParasiteCollector(None, pool_address=ADDRESS)

    def test_404_raises_clear_error(self, monkeypatch):
        class FakeResponse:
            status_code = 404

            def raise_for_status(self):
                raise AssertionError('should not raise_for_status on 404')

            def json(self):
                return {'error': 'User not found'}

        monkeypatch.setattr(
            'collectors.parasite_collector.requests.get',
            lambda *a, **k: FakeResponse(),
        )
        with pytest.raises(ValueError, match='not found'):
            self.collector.fetch_user_stats()


def _iso(moment):
    return moment.strftime('%Y-%m-%dT%H:%M:%S.000Z')


class TestParasiteWindowInference:
    def setup_method(self):
        self.now = datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc)
        self.collector = ParasiteCollector(None, pool_address=ADDRESS)

    def _point(self, minutes_ago, ghs):
        return {
            'timestamp': _iso(self.now - timedelta(minutes=minutes_ago)),
            'hashrate': ghs * 1_000_000_000,
        }

    def test_history_fills_each_window(self):
        history = {
            '1m': [
                self._point(59, 600),
                self._point(30, 600),
                self._point(5, 100),
                self._point(4, 200),
                self._point(3, 300),
                self._point(2, 400),
                self._point(1, 500),
            ],
            '1d': [
                self._point(60 * 30, 9000),
                self._point(60, 1000),
                self._point(30, 2000),
                self._point(10, 3000),
            ],
            '7d': [
                self._point(60 * 24 * 8, 100),
                self._point(60 * 24, 4000),
                self._point(60, 6000),
            ],
        }
        snap = self.collector.normalize_stats(
            sample_user(hashrate=999_000_000_000),
            history=history,
            now=self.now,
        )
        assert snap.hashrate_1m_ghs == pytest.approx(500.0)
        assert snap.hashrate_5m_ghs == pytest.approx(300.0)
        assert snap.hashrate_1h_ghs == pytest.approx(385.7142857)
        assert snap.hashrate_1d_ghs == pytest.approx(2000.0)
        assert snap.hashrate_7d_ghs == pytest.approx(5000.0)
        assert snap.details['hashrate_windows'] == {
            '1m': 'history',
            '5m': 'history',
            '1h': 'history',
            '1d': 'history',
            '7d': 'history',
        }
        assert snap.shares is None

    def test_stale_minute_sample_falls_back_to_live_rate(self):
        history = {'1m': [self._point(10, 100)]}
        snap = self.collector.normalize_stats(
            sample_user(hashrate=500_000_000_000),
            history=history,
            now=self.now,
        )
        assert snap.hashrate_1m_ghs == pytest.approx(500.0)
        assert snap.hashrate_5m_ghs == pytest.approx(500.0)
        assert snap.hashrate_1h_ghs == pytest.approx(100.0)
        assert snap.details['hashrate_windows']['1m'] == 'live'
        assert snap.details['hashrate_windows']['1h'] == 'history'

    def test_hour_falls_back_to_five_minute_series(self):
        history = {'1d': [self._point(20, 800), self._point(10, 1200)]}
        windows = ParasiteCollector.infer_hashrate_windows(
            None,
            history=history,
            now=self.now,
        )
        assert windows['1m'] is None
        assert windows['1h'] == pytest.approx(1000 * 1_000_000_000)

    def test_relative_submission_when_workers_have_no_unix(self):
        user = sample_user(workerData=[], lastSubmission='3m ago')
        snap = self.collector.normalize_stats(user, now=self.now)
        assert snap.last_share_unix == int(self.now.timestamp()) - 180

    def test_fetch_user_history_skips_failed_series(self, monkeypatch):
        def fake(self, path):
            if 'interval=1m' in path:
                return [{'timestamp': '2026-09-27T13:00:00.000Z', 'hashrate': 1}]
            if 'interval=5m' in path:
                raise RuntimeError('down')
            return {'error': 'nope'}

        monkeypatch.setattr(ParasiteCollector, '_fetch_json_once', fake)
        history = self.collector.fetch_user_history()
        assert list(history) == ['1m']

    def test_collect_passes_history(self, monkeypatch):
        stored = {}

        monkeypatch.setattr(
            self.collector,
            'fetch_user_stats',
            lambda: sample_user(),
        )
        monkeypatch.setattr(self.collector, 'fetch_pool_stats', lambda: sample_pool())
        monkeypatch.setattr(self.collector, 'fetch_user_history', lambda: {'1m': []})

        def store(user, pool=None, history=None):
            stored['user'] = user
            stored['pool'] = pool
            stored['history'] = history

        monkeypatch.setattr(self.collector, 'store_pool_stats', store)
        self.collector.collect()
        assert stored['history'] == {'1m': []}
        assert stored['user']['workers'] == 2
        assert stored['pool']['users'] == 2326
