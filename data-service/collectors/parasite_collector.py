"""Parasite Pool statistics collector.

Uses the public parasite.space stats API (no auth token):
- GET /user/{address} — current hashrate, workers, best difficulty
- GET /user/{address}/historical — samples used to fill dashboard windows
- GET /pool-stats — pool-wide totals (optional)

The live user payload has one hashrate. The mining UI reads five windows, so
those are derived from history:

- 1m: latest 1-minute sample
- 5m: mean of 1-minute samples over 5 minutes
- 1h: mean of 1-minute samples over the hour
- 1d: mean of 5-minute samples over the day
- 7d: mean of hourly samples over 7 days

If the short series is missing, the live rate fills 1m and 5m. Longer windows
stay empty instead of copying that live rate. Share totals are not inferred;
Parasite does not publish a cumulative share counter.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
from collectors.normalized import NormalizedPoolSnapshot, PoolDataWriter
from retrying import retry

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = 'https://parasite.space/api'

_DIFFICULTY_RE = re.compile(
    r'^\s*([\d.]+)\s*([KkMmGgTtPpEeZzYy]?)\s*$'
)
_AGO_RE = re.compile(r'^\s*(\d+)\s*([smhd])', re.IGNORECASE)
_HISTORY_QUERIES = (
    ('1m', 'period=1h&interval=1m'),
    ('1d', 'period=1d&interval=5m'),
    ('7d', 'period=7d&interval=1h'),
)
_WINDOW_1M = 180
_WINDOW_5M = 300
_WINDOW_1H = 3600
_WINDOW_1D = 86400
_WINDOW_7D = 7 * 86400
_SI_MULT = {
    '': 1.0,
    'K': 1e3,
    'M': 1e6,
    'G': 1e9,
    'T': 1e12,
    'P': 1e15,
    'E': 1e18,
    'Z': 1e21,
    'Y': 1e24,
}


class ParasiteCollector:
    """Opt-in, read-only collector for Parasite Pool (parasite.space)."""

    def __init__(
        self,
        db_connection,
        pool_url=DEFAULT_API_BASE,
        pool_address=None,
    ):
        self.db = db_connection
        self.pool_url = self._normalize_base_url(pool_url)
        self.pool_address = pool_address
        logger.info(
            "Initialized Parasite collector for address: %s at %s",
            pool_address,
            self.pool_url,
        )

    @staticmethod
    def _normalize_base_url(pool_url):
        base = (pool_url or DEFAULT_API_BASE).rstrip('/')
        if not base.endswith('/api'):
            base = f"{base}/api"
        return base

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _fetch_json(self, path):
        url = f"{self.pool_url}{path}"
        logger.info("Fetching Parasite stats from: %s", url)
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            raise ValueError(
                "Parasite user not found (404). Confirm the address is mining "
                "on Parasite and is not set to private on parasite.space."
            )
        response.raise_for_status()
        return response.json()

    def _fetch_json_once(self, path):
        """Single attempt for optional history. A miss must not stall the poll."""
        url = f"{self.pool_url}{path}"
        logger.info("Fetching Parasite stats from: %s", url)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def fetch_user_stats(self):
        if not self.pool_address:
            logger.error("No Parasite address configured")
            return None
        return self._fetch_json(f"/user/{quote(self.pool_address, safe='')}")

    def fetch_pool_stats(self):
        return self._fetch_json("/pool-stats")

    def fetch_user_history(self):
        """Best-effort window samples. Missing series are omitted, not fatal."""
        if not self.pool_address:
            return {}
        encoded = quote(self.pool_address, safe='')
        history = {}
        for key, query in _HISTORY_QUERIES:
            path = f"/user/{encoded}/historical?{query}"
            try:
                data = self._fetch_json_once(path)
            except Exception as exc:
                logger.warning(
                    "Could not fetch Parasite %s history (non-critical): %s",
                    key,
                    exc,
                )
                continue
            if isinstance(data, list):
                history[key] = data
            else:
                logger.warning("Parasite %s history was not a list", key)
        return history

    @staticmethod
    def _hs_to_ghs(value):
        if value is None or value == '':
            return None
        try:
            return float(value) / 1_000_000_000
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_hashrate_hs(value):
        if value is None or value == '':
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        for threshold, suffix in ((1e15, 'P'), (1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'K')):
            if abs(value) >= threshold:
                return f"{value / threshold:.2f}{suffix}"
        return f"{value:.2f}"

    @staticmethod
    def parse_difficulty(value):
        """Parse numeric or SI-suffixed difficulty (e.g. '63.3T', 1e9) to float."""
        if value is None or value == '':
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text or text in {'?', '??'}:
            return None
        match = _DIFFICULTY_RE.match(text)
        if not match:
            try:
                return float(text)
            except (TypeError, ValueError):
                return None
        num = float(match.group(1))
        unit = (match.group(2) or '').upper()
        return num * _SI_MULT.get(unit, 1.0)

    @staticmethod
    def _number(value, cast=float):
        if value is None or value == '':
            return None
        try:
            return cast(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_ts(value):
        if value is None or value == '':
            return None
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        if text.replace('.', '', 1).isdigit():
            return ParasiteCollector._parse_ts(float(text))
        text = text.replace('Z', '+00:00')
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _series_points(series):
        points = []
        for entry in series or []:
            if not isinstance(entry, dict):
                continue
            ts = ParasiteCollector._parse_ts(entry.get('timestamp'))
            try:
                hashrate = float(entry.get('hashrate'))
            except (TypeError, ValueError):
                continue
            if ts is None or hashrate < 0:
                continue
            points.append((ts, hashrate))
        points.sort(key=lambda point: point[0])
        return points

    @staticmethod
    def _mean_since(points, now, seconds):
        cutoff = now - timedelta(seconds=seconds)
        values = [hashrate for ts, hashrate in points if ts >= cutoff]
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _latest_since(points, now, seconds):
        cutoff = now - timedelta(seconds=seconds)
        recent = [hashrate for ts, hashrate in points if ts >= cutoff]
        if not recent:
            return None
        return recent[-1]

    @staticmethod
    def _live_hs(value):
        if value is None or value == '':
            return None
        try:
            hashrate = float(value)
        except (TypeError, ValueError):
            return None
        if hashrate < 0:
            return None
        return hashrate

    @classmethod
    def infer_hashrate_windows(cls, live_hs, history=None, now=None):
        """Fill dashboard windows from history, with a live fallback for 1m/5m."""
        now = now or datetime.now(timezone.utc)
        history = history or {}
        points_1m = cls._series_points(history.get('1m'))
        points_1d = cls._series_points(history.get('1d'))
        points_7d = cls._series_points(history.get('7d'))
        live = cls._live_hs(live_hs)

        computed = {
            '1m': cls._latest_since(points_1m, now, _WINDOW_1M),
            '5m': cls._mean_since(points_1m, now, _WINDOW_5M),
            '1h': cls._mean_since(points_1m, now, _WINDOW_1H),
            '1d': cls._mean_since(points_1d, now, _WINDOW_1D),
            '7d': cls._mean_since(points_7d, now, _WINDOW_7D),
        }
        if computed['1h'] is None:
            computed['1h'] = cls._mean_since(points_1d, now, _WINDOW_1H)

        sources = {}
        values = {}
        for name, value in computed.items():
            if value is not None:
                values[name] = value
                sources[name] = 'history'
            elif name in {'1m', '5m'} and live is not None:
                values[name] = live
                sources[name] = 'live'
            else:
                values[name] = None
                sources[name] = None
        values['sources'] = sources
        return values

    @staticmethod
    def _coerce_unix(value):
        if value is None or isinstance(value, bool) or value == '':
            return None
        if isinstance(value, str) and not value.strip().replace('.', '', 1).isdigit():
            return None
        try:
            ts = int(float(value))
        except (TypeError, ValueError):
            return None
        if ts > 10**12:
            ts //= 1000
        if ts < 1_000_000_000:
            return None
        return ts

    @staticmethod
    def _relative_ago_unix(value, now):
        if not value:
            return None
        match = _AGO_RE.match(str(value))
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2).lower()
        seconds = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
        return int(now.timestamp()) - amount * seconds

    @classmethod
    def latest_submission_unix(cls, user_data, now=None):
        """Newest worker submission, or a parsed '19s ago' style fallback."""
        now = now or datetime.now(timezone.utc)
        latest = None
        for worker in user_data.get('workerData') or []:
            if not isinstance(worker, dict):
                continue
            ts = cls._coerce_unix(worker.get('lastSubmission'))
            if ts is not None and (latest is None or ts > latest):
                latest = ts
        if latest is not None:
            return latest
        return cls._relative_ago_unix(user_data.get('lastSubmission'), now)

    def normalize_stats(self, user_data, pool_data=None, history=None, now=None) -> NormalizedPoolSnapshot:
        now = now or datetime.now(timezone.utc)
        windows = self.infer_hashrate_windows(
            user_data.get('hashrate'),
            history=history,
            now=now,
        )
        best = self.parse_difficulty(user_data.get('bestDifficulty'))
        workers = self._number(user_data.get('workers'), int)

        details = {
            'source': 'parasite',
            'uptime': user_data.get('uptime'),
            'last_submission': user_data.get('lastSubmission'),
            'workers': user_data.get('workerData') or [],
            'hashrate_windows': windows['sources'],
        }
        if pool_data:
            details.update({
                'pool_highest_difficulty': pool_data.get('highestDifficulty'),
                'pool_workers': pool_data.get('workers'),
                'pool_uptime': pool_data.get('uptime'),
                'last_block_time': pool_data.get('lastBlockTime'),
                'last_block_hash': pool_data.get('lastBlockHash'),
                'work_since_last_block': pool_data.get('workSinceLastBlock'),
            })

        pool_hashrate_ghs = None
        pool_total_miners = None
        if pool_data:
            pool_hashrate_ghs = self._hs_to_ghs(pool_data.get('hashrate'))
            pool_total_miners = self._number(pool_data.get('users'), int)

        return NormalizedPoolSnapshot(
            pool_type='parasite',
            pool_address=self.pool_address,
            pool_url=self.pool_url,
            recorded_at=now,
            hashrate_1m_ghs=self._hs_to_ghs(windows['1m']),
            hashrate_5m_ghs=self._hs_to_ghs(windows['5m']),
            hashrate_1h_ghs=self._hs_to_ghs(windows['1h']),
            hashrate_1d_ghs=self._hs_to_ghs(windows['1d']),
            hashrate_7d_ghs=self._hs_to_ghs(windows['7d']),
            hashrate_1m_display=self._format_hashrate_hs(windows['1m']),
            hashrate_5m_display=self._format_hashrate_hs(windows['5m']),
            hashrate_1h_display=self._format_hashrate_hs(windows['1h']),
            hashrate_1d_display=self._format_hashrate_hs(windows['1d']),
            hashrate_7d_display=self._format_hashrate_hs(windows['7d']),
            workers=workers,
            shares=None,
            best_share=best,
            best_ever=best,
            last_share_unix=self.latest_submission_unix(user_data, now),
            authorised_unix=None,
            pool_total_miners=pool_total_miners,
            pool_total_hashrate_ghs=pool_hashrate_ghs,
            details=details,
        )

    def store_pool_stats(self, user_data, pool_data=None, history=None):
        if not user_data:
            logger.warning("No Parasite user data to store")
            return
        snapshot = self.normalize_stats(user_data, pool_data, history=history)
        PoolDataWriter(connection=self.db).write_snapshot(snapshot)
        logger.info(
            "Stored Parasite stats: 1m=%s 5m=%s 1h=%s 1d=%s 7d=%s (%s workers) @ %s",
            snapshot.hashrate_1m_display,
            snapshot.hashrate_5m_display,
            snapshot.hashrate_1h_display,
            snapshot.hashrate_1d_display,
            snapshot.hashrate_7d_display,
            snapshot.workers,
            snapshot.recorded_at,
        )

    def collect(self):
        logger.info("Starting Parasite data collection...")
        user_data = self.fetch_user_stats()
        if not user_data:
            logger.warning("No data collected from Parasite")
            return
        if isinstance(user_data, dict) and user_data.get('error'):
            raise ValueError(f"Parasite API error: {user_data['error']}")
        pool_data = None
        try:
            pool_data = self.fetch_pool_stats()
        except Exception as exc:
            logger.warning("Could not fetch Parasite pool totals (non-critical): %s", exc)
        history = self.fetch_user_history()
        self.store_pool_stats(user_data, pool_data, history=history)
        logger.info("Parasite data collection completed successfully")


def collect_parasite_data(
    db_connection,
    pool_address,
    pool_url=DEFAULT_API_BASE,
):
    collector = ParasiteCollector(
        db_connection,
        pool_url=pool_url,
        pool_address=pool_address,
    )
    collector.collect()
