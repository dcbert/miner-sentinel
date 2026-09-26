"""BTC PoW Lab pool statistics collector.

The public API exposes address statistics in H/s and pool totals in TH/s.
This adapter preserves the API's real averaging windows and rejects stale
address responses instead of storing them as current measurements.
"""
import logging
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from collectors.normalized import NormalizedPoolSnapshot, PoolDataWriter
from retrying import retry

logger = logging.getLogger(__name__)


class BTCPoWLabCollector:
    """Opt-in, read-only collector for BTC PoW Lab Hybrid Solo."""

    def __init__(
        self,
        db_connection,
        pool_url="https://btcpowlab-pool.com/public/v1",
        pool_address=None,
        max_age_seconds=300,
    ):
        self.db = db_connection
        self.pool_url = pool_url.rstrip('/')
        self.pool_address = pool_address
        self.max_age_seconds = max_age_seconds
        logger.info("Initialized BTC PoW Lab collector for address: %s", pool_address)

    def _validate_freshness(self, data):
        generated_at = data.get('generated_at')
        if not isinstance(generated_at, (int, float)):
            raise ValueError("BTC PoW Lab response is missing generated_at")
        age_seconds = time.time() - float(generated_at)
        if age_seconds > self.max_age_seconds:
            raise ValueError(
                f"BTC PoW Lab response is stale ({age_seconds:.0f}s old, "
                f"limit {self.max_age_seconds}s)"
            )
        return float(generated_at)

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _fetch_json(self, path):
        url = f"{self.pool_url}{path}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        self._validate_freshness(data)
        return data

    def fetch_miner_stats(self):
        if not self.pool_address:
            logger.error("No BTC PoW Lab address configured")
            return None
        return self._fetch_json(f"/miner/{quote(self.pool_address, safe='')}")

    def fetch_pool_stats(self):
        return self._fetch_json("/pool")

    @staticmethod
    def _hs_to_ghs(value):
        if value is None:
            return None
        try:
            return float(value) / 1_000_000_000
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ths_to_ghs(value):
        if value is None:
            return None
        try:
            return float(value) * 1000
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _number(value, cast=float):
        if value is None or value == '':
            return None
        try:
            return cast(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_hashrate_hs(value):
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        for threshold, suffix in ((1e15, 'P'), (1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'K')):
            if abs(value) >= threshold:
                return f"{value / threshold:.2f}{suffix}"
        return f"{value:.2f}"

    def normalize_stats(self, miner_data, pool_data=None) -> NormalizedPoolSnapshot:
        generated_at = self._validate_freshness(miner_data)
        h5m = miner_data.get('hashrate_5m_hs')
        h1h = miner_data.get('hashrate_1h_hs')
        h24h = miner_data.get('hashrate_24h_hs')

        pool = (pool_data or {}).get('pool') or {}
        pool_hashrate_1h_ths = pool.get('hashrate_1h_ths')
        details = {
            'source': 'btcpowlab',
            'model': 'Hybrid Solo',
            'api_generated_at': generated_at,
        }
        if pool_data:
            details.update({
                'pool_hashrate_15m_ghs': self._ths_to_ghs(pool.get('hashrate_15m_ths')),
                'pool_economics': pool_data.get('economics'),
                'community_eligible_work_share': miner_data.get('community_eligible_work_share'),
                'community_tier': miner_data.get('community_tier'),
            })

        return NormalizedPoolSnapshot(
            pool_type='btcpowlab',
            pool_address=self.pool_address,
            pool_url=self.pool_url,
            recorded_at=datetime.fromtimestamp(generated_at, tz=timezone.utc),
            # The API does not expose a one-minute address window.
            hashrate_1m_ghs=None,
            hashrate_5m_ghs=self._hs_to_ghs(h5m),
            hashrate_1h_ghs=self._hs_to_ghs(h1h),
            hashrate_1d_ghs=self._hs_to_ghs(h24h),
            hashrate_7d_ghs=None,
            hashrate_1m_display=None,
            hashrate_5m_display=self._format_hashrate_hs(h5m),
            hashrate_1h_display=self._format_hashrate_hs(h1h),
            hashrate_1d_display=self._format_hashrate_hs(h24h),
            hashrate_7d_display=None,
            workers=self._number(miner_data.get('workers_online'), int),
            shares=self._number(miner_data.get('accepted_shares'), int),
            best_share=self._number(miner_data.get('best_share_difficulty')),
            best_ever=self._number(miner_data.get('best_share_difficulty')),
            last_share_unix=self._number(miner_data.get('last_share_at'), int),
            authorised_unix=None,
            pool_total_miners=self._number(pool.get('active_miners'), int),
            pool_total_hashrate_ghs=self._ths_to_ghs(pool_hashrate_1h_ths),
            details=details,
        )

    def store_pool_stats(self, miner_data, pool_data=None):
        if not miner_data:
            logger.warning("No BTC PoW Lab miner data to store")
            return
        snapshot = self.normalize_stats(miner_data, pool_data)
        PoolDataWriter(connection=self.db).write_snapshot(snapshot)

    def collect(self):
        miner_data = self.fetch_miner_stats()
        if not miner_data:
            return
        pool_data = None
        try:
            pool_data = self.fetch_pool_stats()
        except Exception as exc:
            logger.warning("Could not fetch BTC PoW Lab pool totals (non-critical): %s", exc)
        self.store_pool_stats(miner_data, pool_data)


def collect_btcpowlab_data(
    db_connection,
    pool_address,
    pool_url="https://btcpowlab-pool.com/public/v1",
):
    collector = BTCPoWLabCollector(
        db_connection,
        pool_url=pool_url,
        pool_address=pool_address,
    )
    collector.collect()
