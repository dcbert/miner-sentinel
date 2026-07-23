"""Tests for unification migration helpers and full data copy."""
import pytest
from django.utils import timezone

from api.migration_utils import (
    convert_hashrate_str_to_ghs,
    migrate_legacy_to_unified,
    reverse_unified_data,
    verify_unification_counts,
)
from api.models import (
    AvalonDevice,
    AvalonHardwareLogs,
    AvalonMiningStats,
    AvalonSystemInfo,
    BitAxeDevice,
    BitAxeHardwareLog,
    BitAxeMiningStats,
    BitAxePoolStats,
    BitAxeSystemInfo,
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)


class FakeApps:
    """Minimal apps.get_model shim using live models (syncdb / no migrations)."""

    def get_model(self, app_label, model_name):
        import api.models as m
        return getattr(m, model_name)


@pytest.mark.parametrize(
    'raw,expected',
    [
        ('466G', 466.0),
        ('1.29T', 1290.0),
        ('185M', 0.185),
        ('1000K', 0.001),
        ('', None),
        (None, None),
        (12.5, 12.5),
    ],
)
def test_convert_hashrate_str_to_ghs(raw, expected):
    result = convert_hashrate_str_to_ghs(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


@pytest.mark.django_db
def test_migrate_empty_legacy():
    result = migrate_legacy_to_unified(FakeApps(), None)
    assert result['devices'] == 0
    assert result['mining'] == 0
    assert result['pool'] == 0


@pytest.mark.django_db
def test_migrate_bitaxe_only_preserves_values():
    now = timezone.now()
    dev = BitAxeDevice.objects.create(
        device_id='bx-1',
        device_name='Bitaxe Test',
        ip_address='192.168.1.10',
        is_active=True,
    )
    BitAxeMiningStats.objects.create(
        device=dev,
        recorded_at=now,
        hashrate_ghs=450.5,
        shares_accepted=100,
        shares_rejected=2,
        uptime_seconds=3600,
        best_difficulty=1_000_000,
        best_session_difficulty=50_000,
        pool_url='stratum+tcp://pool',
        pool_user='user',
    )
    BitAxeHardwareLog.objects.create(
        device=dev,
        recorded_at=now,
        power_watts=18.0,
        efficiency_j_per_th=40.0,
        temperature_c=52.5,
        fan_speed_rpm=3000,
        voltage=1.2,
        frequency_mhz=500,
    )
    BitAxeSystemInfo.objects.create(
        device=dev,
        recorded_at=now,
        asic_model='BM1366',
        hostname='bitaxe',
        version='2.0.0',
        free_heap=12345,
    )

    result = migrate_legacy_to_unified(FakeApps(), None)
    assert result['devices'] == 1
    assert result['mining'] == 1
    assert result['hardware'] == 1
    assert result['system'] == 1

    u = Device.objects.get(make='bitaxe', device_id='bx-1')
    assert u.name == 'Bitaxe Test'
    assert u.protocol == 'http_axeos'

    m = DeviceMiningStats.objects.get(device=u)
    assert m.hashrate_ghs == pytest.approx(450.5)
    assert m.best_difficulty == pytest.approx(1_000_000)
    assert m.best_session_difficulty == pytest.approx(50_000)
    assert m.recorded_at == now

    h = DeviceHardwareStats.objects.get(device=u)
    assert h.temperature_c == pytest.approx(52.5)
    assert h.frequency_mhz == pytest.approx(500.0)

    s = DeviceSystemInfo.objects.get(device=u)
    assert s.hostname == 'bitaxe'
    assert s.details.get('asic_model') == 'BM1366'
    assert s.details.get('free_heap') == 12345


@pytest.mark.django_db
def test_migrate_avalon_difficulty_mapping():
    now = timezone.now()
    dev = AvalonDevice.objects.create(
        device_id='av-1',
        device_name='Avalon Test',
        ip_address='192.168.1.20',
    )
    AvalonMiningStats.objects.create(
        device=dev,
        recorded_at=now,
        hashrate_ghs=4.5,
        shares_accepted=10,
        shares_rejected=1,
        uptime_seconds=100,
        difficulty=9_999.5,
    )
    AvalonHardwareLogs.objects.create(
        device=dev,
        recorded_at=now,
        power_watts=80.0,
        efficiency_j_per_th=17.0,
        temperature_c=60.0,
        frequency_mhz=464.89,
    )
    AvalonSystemInfo.objects.create(
        device=dev,
        recorded_at=now,
        device_model='Nano3s',
        serial_number='DNA123',
        firmware_version='cgminer',
    )

    migrate_legacy_to_unified(FakeApps(), None)
    u = Device.objects.get(make='avalon', device_id='av-1')
    assert u.port == 4028
    m = DeviceMiningStats.objects.get(device=u)
    assert m.best_difficulty == pytest.approx(9_999.5)
    assert m.best_session_difficulty is None


@pytest.mark.django_db
def test_migrate_colliding_device_ids():
    BitAxeDevice.objects.create(
        device_id='miner-1', device_name='B', ip_address='10.0.0.1'
    )
    AvalonDevice.objects.create(
        device_id='miner-1', device_name='A', ip_address='10.0.0.2'
    )
    migrate_legacy_to_unified(FakeApps(), None)
    assert Device.objects.filter(device_id='miner-1').count() == 2


@pytest.mark.django_db
def test_migrate_pool_stats_and_type_from_settings():
    CollectorSettings.objects.create(
        pk=1,
        pool_type='publicpool',
        publicpool_address='bc1qxyz',
    )
    BitAxePoolStats.objects.create(
        pool_address='bc1qxyz',
        recorded_at=timezone.now(),
        hashrate_1m='100G',
        hashrate_5m='90G',
        hashrate_1hr='80G',
        hashrate_1d='70G',
        hashrate_7d='60G',
        lastshare=1_700_000_000,
        workers=3,
        shares=1000,
        bestshare=1e9,
        bestever=2e9,
        authorised=1_600_000_000,
        hashrate_1m_ghs=100.0,
        hashrate_1d_ghs=70.0,
    )
    migrate_legacy_to_unified(FakeApps(), None)
    p = PoolStats.objects.get()
    assert p.pool_type == 'publicpool'
    assert p.hashrate_1m_ghs == pytest.approx(100.0)
    assert p.hashrate_1d_ghs == pytest.approx(70.0)
    assert p.hashrate_1m_display == '100G'
    assert p.workers == 3
    assert p.best_share == pytest.approx(1e9)


@pytest.mark.django_db
def test_migrate_idempotent():
    BitAxeDevice.objects.create(
        device_id='bx-idemp', device_name='B', ip_address='10.0.0.3'
    )
    migrate_legacy_to_unified(FakeApps(), None)
    first = Device.objects.count()
    result = migrate_legacy_to_unified(FakeApps(), None)
    assert Device.objects.count() == first
    assert result.get('skipped') == 1 or result['devices'] == first


@pytest.mark.django_db
def test_migrate_mixed_fleet_counts():
    now = timezone.now()
    b = BitAxeDevice.objects.create(device_id='b1', device_name='B', ip_address='1.1.1.1')
    a = AvalonDevice.objects.create(device_id='a1', device_name='A', ip_address='2.2.2.2')
    for i in range(5):
        BitAxeMiningStats.objects.create(
            device=b, recorded_at=now, hashrate_ghs=float(i),
            shares_accepted=i, shares_rejected=0, uptime_seconds=i,
        )
        AvalonMiningStats.objects.create(
            device=a, recorded_at=now, hashrate_ghs=float(i),
            shares_accepted=i, shares_rejected=0, uptime_seconds=i, difficulty=1.0,
        )
    result = migrate_legacy_to_unified(FakeApps(), None)
    assert result['devices'] == 2
    assert result['mining'] == 10
    assert verify_unification_counts()['ok'] is True


@pytest.mark.django_db
def test_reverse_clears_unified_only():
    BitAxeDevice.objects.create(device_id='bx-r', device_name='B', ip_address='3.3.3.3')
    migrate_legacy_to_unified(FakeApps(), None)
    assert Device.objects.count() == 1
    reverse_unified_data(FakeApps(), None)
    assert Device.objects.count() == 0
    assert BitAxeDevice.objects.count() == 1


@pytest.mark.django_db
def test_verify_detects_mismatch():
    BitAxeDevice.objects.create(device_id='bx-m', device_name='B', ip_address='4.4.4.4')
    # unified empty → mismatch
    result = verify_unification_counts()
    assert result['ok'] is False
