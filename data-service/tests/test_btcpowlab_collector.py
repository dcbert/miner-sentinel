import time

import pytest

from collectors.btcpowlab_collector import BTCPoWLabCollector


ADDRESS = 'bc1qexampleaddress0000000000000000000000000'
API = 'https://btcpowlab-pool.com/public/v1'


def current_miner(**overrides):
    payload = {
        'generated_at': time.time(),
        'hashrate_5m_hs': 500_000_000_000,
        'hashrate_1h_hs': 450_000_000_000,
        'hashrate_24h_hs': 400_000_000_000,
        'workers_online': 2,
        'accepted_shares': 123,
        'best_share_difficulty': '4567.5',
        'last_share_at': 1_700_000_000,
        'community_eligible_work_share': '0.125',
        'community_tier': 'small',
    }
    payload.update(overrides)
    return payload


def current_pool():
    return {
        'generated_at': time.time(),
        'pool': {
            'hashrate_15m_ths': 1.25,
            'hashrate_1h_ths': 1.1,
            'active_miners': 3,
        },
        'economics': {'finder_bps': 8500, 'community_bps': 1000, 'lab_bps': 500},
    }


class TestBTCPoWLabNormalize:
    def setup_method(self):
        self.collector = BTCPoWLabCollector(None, pool_address=ADDRESS)

    def test_preserves_windows_and_converts_units(self):
        snap = self.collector.normalize_stats(current_miner(), current_pool())
        assert snap.pool_type == 'btcpowlab'
        assert snap.hashrate_1m_ghs is None
        assert snap.hashrate_5m_ghs == pytest.approx(500.0)
        assert snap.hashrate_1h_ghs == pytest.approx(450.0)
        assert snap.hashrate_1d_ghs == pytest.approx(400.0)
        assert snap.hashrate_7d_ghs is None
        assert snap.pool_total_hashrate_ghs == pytest.approx(1100.0)
        assert snap.details['pool_hashrate_15m_ghs'] == pytest.approx(1250.0)
        assert snap.details['model'] == 'Hybrid Solo'
        assert snap.workers == 2
        assert snap.shares == 123

    def test_missing_windows_remain_none(self):
        miner = current_miner(
            hashrate_5m_hs=None,
            hashrate_1h_hs=None,
            hashrate_24h_hs=None,
        )
        snap = self.collector.normalize_stats(miner)
        assert snap.hashrate_1m_ghs is None
        assert snap.hashrate_5m_ghs is None
        assert snap.hashrate_1h_ghs is None
        assert snap.hashrate_1d_ghs is None
        assert snap.hashrate_5m_display is None

    def test_stale_response_is_rejected(self):
        miner = current_miner(generated_at=time.time() - 301)
        with pytest.raises(ValueError, match='stale'):
            self.collector.normalize_stats(miner)

    def test_missing_generated_at_is_rejected(self):
        miner = current_miner()
        del miner['generated_at']
        with pytest.raises(ValueError, match='missing generated_at'):
            self.collector.normalize_stats(miner)


def test_fetches_encoded_address_and_pool_endpoint(monkeypatch):
    collector = BTCPoWLabCollector(None, pool_address=ADDRESS)

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    payloads = {
        f'{API}/miner/{ADDRESS}': current_miner(),
        f'{API}/pool': current_pool(),
    }
    monkeypatch.setattr(
        'collectors.btcpowlab_collector.requests.get',
        lambda url, timeout: Response(payloads[url]),
    )
    assert collector.fetch_miner_stats()['accepted_shares'] == 123
    assert collector.fetch_pool_stats()['pool']['active_miners'] == 3
