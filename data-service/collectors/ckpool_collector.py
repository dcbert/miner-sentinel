"""
CKPool data collector for mining pool statistics.
Fetches data from CKPool API, normalizes, dual-writes to pool_stats + legacy.
"""
import logging
import re
from datetime import datetime, timezone

import requests
from collectors.normalized import NormalizedPoolSnapshot, PoolDataWriter
from retrying import retry

logger = logging.getLogger(__name__)


class CKPoolCollector:
    """Collector for CKPool mining pool statistics."""

    def __init__(self, db_connection, pool_url="https://eusolo.ckpool.org", pool_address=None, dual_write=False):
        """
        Initialize CKPool collector.

        Args:
            db_connection: Database connection object (kept for API compat; writer uses DATABASE_URL)
            pool_url: CKPool API base URL
            pool_address: Bitcoin address or pool username
            dual_write: also write legacy bitaxe_pool_stats
        """
        self.db = db_connection
        self.pool_url = pool_url.rstrip('/')
        self.pool_address = pool_address
        self.dual_write = dual_write
        # Derive database URL from connection if possible; writer opened via dsn from conn
        self._dsn = None
        if db_connection is not None:
            try:
                self._dsn = db_connection.dsn
            except Exception:
                self._dsn = None
        logger.info(f"Initialized CKPool collector for address: {pool_address}")

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def fetch_pool_stats(self):
        """
        Fetch pool statistics from CKPool API.

        Returns:
            dict: Pool statistics data
        """
        if not self.pool_address:
            logger.error("No pool address configured")
            return None

        url = f"{self.pool_url}/users/{self.pool_address}"
        logger.info(f"Fetching pool stats from: {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched pool stats: {data.get('hashrate_1m', 'N/A')} (1m)")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch pool stats: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise

    def convert_hashrate_to_ghs(self, hashrate_str):
        """
        Convert hashrate string (e.g., '466G', '1.29G', '185M') to GH/s float.

        Args:
            hashrate_str: Hashrate string from API

        Returns:
            float: Hashrate in GH/s
        """
        if not hashrate_str:
            return 0.0

        # Remove whitespace
        hashrate_str = hashrate_str.strip()

        # Extract number and unit
        match = re.match(r'([\d.]+)([KMGTP]?)', hashrate_str, re.IGNORECASE)
        if not match:
            return 0.0

        value = float(match.group(1))
        unit = match.group(2).upper()

        # Convert to GH/s
        multipliers = {
            '': 1e-9,      # H/s
            'K': 1e-6,     # KH/s
            'M': 0.001,    # MH/s
            'G': 1,        # GH/s
            'T': 1000,     # TH/s
            'P': 1000000,  # PH/s
        }

        return value * multipliers.get(unit, 1)

    def normalize_stats(self, stats_data) -> NormalizedPoolSnapshot:
        """Convert raw CKPool user JSON into NormalizedPoolSnapshot."""
        h1m = stats_data.get('hashrate1m', '0')
        h5m = stats_data.get('hashrate5m', '0')
        h1h = stats_data.get('hashrate1hr', '0')
        h1d = stats_data.get('hashrate1d', '0')
        h7d = stats_data.get('hashrate7d', '0')
        return NormalizedPoolSnapshot(
            pool_type='ckpool',
            pool_address=self.pool_address,
            pool_url=self.pool_url,
            recorded_at=datetime.now(timezone.utc),
            hashrate_1m_ghs=self.convert_hashrate_to_ghs(h1m),
            hashrate_5m_ghs=self.convert_hashrate_to_ghs(h5m),
            hashrate_1h_ghs=self.convert_hashrate_to_ghs(h1h),
            hashrate_1d_ghs=self.convert_hashrate_to_ghs(h1d),
            hashrate_7d_ghs=self.convert_hashrate_to_ghs(h7d),
            hashrate_1m_display=str(h1m) if h1m is not None else None,
            hashrate_5m_display=str(h5m) if h5m is not None else None,
            hashrate_1h_display=str(h1h) if h1h is not None else None,
            hashrate_1d_display=str(h1d) if h1d is not None else None,
            hashrate_7d_display=str(h7d) if h7d is not None else None,
            workers=int(stats_data.get('workers', 0) or 0),
            shares=int(stats_data.get('shares', 0) or 0),
            best_share=float(stats_data.get('bestshare', 0) or 0),
            best_ever=float(stats_data.get('bestever', 0) or 0),
            last_share_unix=int(stats_data.get('lastshare', 0) or 0) or None,
            authorised_unix=int(stats_data.get('authorised', 0) or 0) or None,
            details={'source': 'ckpool'},
        )

    def store_pool_stats(self, stats_data):
        """Store pool statistics via PoolDataWriter (unified + optional legacy)."""
        if not stats_data:
            logger.warning("No stats data to store")
            return

        try:
            snapshot = self.normalize_stats(stats_data)
            database_url = self._resolve_database_url()
            writer = PoolDataWriter(database_url, dual_write=self.dual_write)
            writer.write_snapshot(snapshot)
            logger.info(f"Stored pool stats: {stats_data.get('hashrate1m', 'N/A')} @ {snapshot.recorded_at}")
        except Exception as e:
            logger.error(f"Failed to store pool stats: {e}")
            raise

    def _resolve_database_url(self):
        if self._dsn:
            # psycopg2 dsn is space-separated key=value
            parts = dict(p.split('=', 1) for p in self._dsn.split() if '=' in p)
            user = parts.get('user', 'minersentinel')
            password = parts.get('password', '')
            host = parts.get('host', 'localhost')
            port = parts.get('port', '5432')
            dbname = parts.get('dbname', 'minersentinel')
            return f'postgresql://{user}:{password}@{host}:{port}/{dbname}'
        from decouple import config
        return (
            f"postgresql://{config('POSTGRES_USER', default='minersentinel')}:"
            f"{config('POSTGRES_PASSWORD', default='changeme')}@"
            f"{config('POSTGRES_HOST', default='postgres')}:"
            f"{config('POSTGRES_PORT', default='5432')}/"
            f"{config('POSTGRES_DB', default='minersentinel')}"
        )

    def collect(self):
        """
        Main collection method.
        Fetches and stores pool statistics.
        """
        try:
            logger.info("Starting CKPool data collection...")
            stats_data = self.fetch_pool_stats()

            if stats_data:
                self.store_pool_stats(stats_data)
                logger.info("CKPool data collection completed successfully")
            else:
                logger.warning("No data collected from CKPool")

        except Exception as e:
            logger.error(f"CKPool collection failed: {e}")
            raise


def collect_ckpool_data(db_connection, pool_address, pool_url="https://eusolo.ckpool.org"):
    """
    Convenience function to collect CKPool data.

    Args:
        db_connection: Database connection
        pool_address: Bitcoin address or pool username
        pool_url: CKPool server URL (default: https://eusolo.ckpool.org)
    """
    collector = CKPoolCollector(db_connection, pool_url=pool_url, pool_address=pool_address)
    collector.collect()
