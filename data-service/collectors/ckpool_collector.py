"""
CKPool data collector for Bitaxe mining pool statistics.
Fetches data from CKPool API and stores it in the database.
"""
import logging
import re
from datetime import datetime

import requests
from retrying import retry

logger = logging.getLogger(__name__)


class CKPoolCollector:
    """Collector for CKPool mining pool statistics."""

    def __init__(self, db_connection, pool_url="https://eusolo.ckpool.org", pool_address=None):
        """
        Initialize CKPool collector.

        Args:
            db_connection: Database connection object
            pool_url: CKPool API base URL
            pool_address: Bitcoin address or pool username
        """
        self.db = db_connection
        self.pool_url = pool_url.rstrip('/')
        self.pool_address = pool_address
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

    def store_pool_stats(self, stats_data):
        """
        Store pool statistics in the database.

        Args:
            stats_data: Pool statistics data from API
        """
        if not stats_data:
            logger.warning("No stats data to store")
            return

        try:
            cursor = self.db.cursor()

            # Convert hashrates to GH/s for easier querying
            hashrate_1m_ghs = self.convert_hashrate_to_ghs(stats_data.get('hashrate1m', '0'))
            hashrate_1d_ghs = self.convert_hashrate_to_ghs(stats_data.get('hashrate1d', '0'))

            # Insert pool statistics
            query = """
                INSERT INTO bitaxe_pool_stats (
                    pool_address, recorded_at,
                    hashrate_1m, hashrate_5m, hashrate_1hr, hashrate_1d, hashrate_7d,
                    lastshare, workers, shares, bestshare, bestever, authorised,
                    hashrate_1m_ghs, hashrate_1d_ghs
                ) VALUES (
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s
                )
            """

            values = (
                self.pool_address,
                datetime.now(),
                stats_data.get('hashrate1m', '0'),
                stats_data.get('hashrate5m', '0'),
                stats_data.get('hashrate1hr', '0'),
                stats_data.get('hashrate1d', '0'),
                stats_data.get('hashrate7d', '0'),
                stats_data.get('lastshare', 0),
                stats_data.get('workers', 0),
                stats_data.get('shares', 0),
                stats_data.get('bestshare', 0.0),
                stats_data.get('bestever', 0),
                stats_data.get('authorised', 0),
                hashrate_1m_ghs,
                hashrate_1d_ghs,
            )

            cursor.execute(query, values)
            self.db.commit()
            logger.info(f"Stored pool stats: {stats_data.get('hashrate1m', 'N/A')} @ {datetime.now()}")

        except Exception as e:
            logger.error(f"Failed to store pool stats: {e}")
            self.db.rollback()
            raise

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
