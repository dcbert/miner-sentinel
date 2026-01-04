"""
PublicPool data collector for mining pool statistics.
Fetches data from Public Pool API (https://github.com/benjamin-wilson/public-pool) and stores it in the database.

API Endpoints used:
- GET /api/client/:address - Get client info (workers, hashrate, bestDifficulty)
- GET /api/pool - Get pool-wide stats (totalHashRate, totalMiners, blocksFound)
"""
import logging
from datetime import datetime

import requests
from retrying import retry

logger = logging.getLogger(__name__)


class PublicPoolCollector:
    """Collector for Public Pool mining statistics."""

    def __init__(self, db_connection, pool_url="http://localhost:3334", pool_address=None):
        """
        Initialize PublicPool collector.

        Args:
            db_connection: Database connection object
            pool_url: PublicPool API base URL (e.g., http://localhost:3334 or https://web.public-pool.io/api)
            pool_address: Bitcoin address for user statistics
        """
        self.db = db_connection
        # Ensure URL ends with /api if not already
        self.pool_url = pool_url.rstrip('/')
        if not self.pool_url.endswith('/api'):
            self.pool_url = f"{self.pool_url}/api"
        self.pool_address = pool_address
        logger.info(f"Initialized PublicPool collector for address: {pool_address} at {self.pool_url}")

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def fetch_client_stats(self):
        """
        Fetch client/user statistics from PublicPool API.

        Returns:
            dict: Client statistics data including workers and hashrate
        """
        if not self.pool_address:
            logger.error("No pool address configured")
            return None

        url = f"{self.pool_url}/client/{self.pool_address}"
        logger.info(f"Fetching client stats from: {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched client stats: {data.get('workersCount', 0)} workers")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch client stats: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def fetch_pool_stats(self):
        """
        Fetch pool-wide statistics from PublicPool API.

        Returns:
            dict: Pool statistics data
        """
        url = f"{self.pool_url}/pool"
        logger.info(f"Fetching pool stats from: {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched pool stats: {data.get('totalMiners', 0)} miners, "
                       f"hashrate: {data.get('totalHashRate', 0)}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch pool stats: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise

    def convert_hashrate_to_ghs(self, hashrate_value):
        """
        Convert hashrate value (in H/s) to GH/s.
        PublicPool returns hashrate as raw H/s numbers.

        Args:
            hashrate_value: Hashrate in H/s (can be int or float)

        Returns:
            float: Hashrate in GH/s
        """
        if not hashrate_value:
            return 0.0

        try:
            # PublicPool returns raw H/s values
            return float(hashrate_value) / 1_000_000_000  # Convert H/s to GH/s
        except (ValueError, TypeError):
            return 0.0

    def format_hashrate(self, hashrate_hs):
        """
        Format hashrate from H/s to human-readable string.

        Args:
            hashrate_hs: Hashrate in H/s

        Returns:
            str: Formatted hashrate string (e.g., '466G', '1.29T')
        """
        if not hashrate_hs:
            return '0'

        try:
            value = float(hashrate_hs)
            if value >= 1e15:
                return f"{value/1e15:.2f}P"
            elif value >= 1e12:
                return f"{value/1e12:.2f}T"
            elif value >= 1e9:
                return f"{value/1e9:.2f}G"
            elif value >= 1e6:
                return f"{value/1e6:.2f}M"
            elif value >= 1e3:
                return f"{value/1e3:.2f}K"
            else:
                return f"{value:.2f}"
        except (ValueError, TypeError):
            return '0'

    def store_pool_stats(self, client_data, pool_data=None):
        """
        Store pool statistics in the database.
        Uses the same bitaxe_pool_stats table for compatibility.

        Args:
            client_data: Client statistics data from API (user-specific)
            pool_data: Pool-wide statistics data from API (optional)
        """
        if not client_data:
            logger.warning("No client data to store")
            return

        try:
            cursor = self.db.cursor()

            # Calculate total hashrate from workers
            total_hashrate = 0
            workers_count = client_data.get('workersCount', 0)
            workers = client_data.get('workers', [])

            for worker in workers:
                worker_hashrate = worker.get('hashRate', 0)
                if worker_hashrate:
                    total_hashrate += float(worker_hashrate)

            # Format hashrates for storage
            hashrate_formatted = self.format_hashrate(total_hashrate)
            hashrate_ghs = self.convert_hashrate_to_ghs(total_hashrate)

            # Get best difficulty from client data
            best_difficulty = client_data.get('bestDifficulty', 0) or 0

            # Get pool-wide data if available
            pool_total_hashrate = 0
            pool_total_miners = 0
            if pool_data:
                pool_total_hashrate = pool_data.get('totalHashRate', 0) or 0
                pool_total_miners = pool_data.get('totalMiners', 0) or 0

            # Insert pool statistics (compatible with existing table structure)
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
                hashrate_formatted,  # hashrate_1m - current hashrate
                hashrate_formatted,  # hashrate_5m - same for PublicPool (no 5m stat)
                hashrate_formatted,  # hashrate_1hr - same for PublicPool
                hashrate_formatted,  # hashrate_1d - same for PublicPool
                hashrate_formatted,  # hashrate_7d - same for PublicPool
                0,                   # lastshare - not available from API
                workers_count,       # workers count
                0,                   # shares - not directly available
                best_difficulty,     # bestshare - user's best difficulty
                best_difficulty,     # bestever - same as bestshare for now
                pool_total_miners,   # authorised - store total pool miners here
                hashrate_ghs,        # hashrate_1m_ghs
                hashrate_ghs,        # hashrate_1d_ghs
            )

            cursor.execute(query, values)
            self.db.commit()
            logger.info(f"Stored PublicPool stats: {hashrate_formatted} ({workers_count} workers) @ {datetime.now()}")

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
            logger.info("Starting PublicPool data collection...")

            # Fetch client-specific stats
            client_data = self.fetch_client_stats()

            # Optionally fetch pool-wide stats
            pool_data = None
            try:
                pool_data = self.fetch_pool_stats()
            except Exception as e:
                logger.warning(f"Could not fetch pool-wide stats (non-critical): {e}")

            if client_data:
                self.store_pool_stats(client_data, pool_data)
                logger.info("PublicPool data collection completed successfully")
            else:
                logger.warning("No data collected from PublicPool")

        except Exception as e:
            logger.error(f"PublicPool collection failed: {e}")
            raise


def collect_publicpool_data(db_connection, pool_address, pool_url="http://localhost:3334"):
    """
    Convenience function to collect PublicPool data.

    Args:
        db_connection: Database connection
        pool_address: Bitcoin address for user statistics
        pool_url: PublicPool API URL (default: http://localhost:3334)
    """
    collector = PublicPoolCollector(db_connection, pool_url=pool_url, pool_address=pool_address)
    collector.collect()
