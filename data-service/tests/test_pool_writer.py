"""Unit tests for PoolDataWriter (Release C: pool_stats only)."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.normalized import NormalizedPoolSnapshot, PoolDataWriter


def _pool_snap():
    return NormalizedPoolSnapshot(
        pool_type='ckpool',
        pool_address='bc1qtest',
        pool_url='https://eusolo.ckpool.org',
        recorded_at=datetime.now(timezone.utc),
        hashrate_1m_ghs=466.0,
        hashrate_5m_ghs=450.0,
        hashrate_1h_ghs=400.0,
        hashrate_1d_ghs=1290.0,
        hashrate_7d_ghs=1000.0,
        hashrate_1m_display='466G',
        hashrate_5m_display='450G',
        hashrate_1h_display='400G',
        hashrate_1d_display='1.29T',
        hashrate_7d_display='1T',
        workers=2,
        shares=100,
        best_share=1e12,
        best_ever=2e12,
        last_share_unix=1700000000,
        authorised_unix=1600000000,
        pool_total_miners=None,
        pool_total_hashrate_ghs=None,
        details={},
    )


@patch('collectors.normalized.psycopg2.connect')
def test_pool_writer_insert(mock_connect):
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.closed = 0
    mock_connect.return_value = mock_conn

    writer = PoolDataWriter(database_url='postgresql://u:p@localhost/db', dual_write=True)
    writer.write_snapshot(_pool_snap())

    sqls = ' '.join(str(c) for c in mock_cursor.execute.call_args_list)
    assert 'INSERT INTO pool_stats' in sqls or 'pool_stats' in sqls
    assert 'bitaxe_pool_stats' not in sqls  # dual_write ignored in Release C
    mock_conn.commit.assert_called()
    mock_conn.close.assert_called()


def test_pool_writer_shared_connection_not_closed():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.closed = 0

    writer = PoolDataWriter(connection=mock_conn, dual_write=False)
    writer.write_snapshot(_pool_snap())
    mock_conn.commit.assert_called()
    mock_conn.close.assert_not_called()
