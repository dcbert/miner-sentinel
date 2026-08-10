"""
Tests for unification migration helpers.

Release C removed live legacy ORM models. Full legacy→unified copy is still
exercised by migration 0012 against historical models in real migrate runs.
Here we cover pure helpers, reverse, and Release C verify behavior.
"""
import pytest
from django.utils import timezone

from api.migration_utils import (
    convert_hashrate_str_to_ghs,
    reverse_unified_data,
    verify_unification_counts,
)
from api.models import (
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)


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
def test_verify_unification_release_c_no_legacy():
    result = verify_unification_counts()
    assert result['legacy_available'] is False
    assert result['ok'] is True
    assert 'devices' in result['unified']


class FakeApps:
    def get_model(self, app_label, model_name):
        import api.models as m
        return getattr(m, model_name)


@pytest.mark.django_db
def test_reverse_unified_data_clears_unified_only():
    d = Device.objects.create(
        device_id='bx-r',
        name='B',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='3.3.3.3',
    )
    now = timezone.now()
    DeviceMiningStats.objects.create(
        device=d, recorded_at=now, hashrate_ghs=1, shares_accepted=0,
        shares_rejected=0, uptime_seconds=1,
    )
    DeviceHardwareStats.objects.create(device=d, recorded_at=now, temperature_c=40)
    DeviceSystemInfo.objects.create(device=d, recorded_at=now, hostname='h')
    PoolStats.objects.create(
        pool_type='ckpool', pool_address='a', recorded_at=now, hashrate_1m_ghs=1,
    )
    assert Device.objects.count() == 1
    reverse_unified_data(FakeApps(), None)
    assert Device.objects.count() == 0
    assert DeviceMiningStats.objects.count() == 0
    assert PoolStats.objects.count() == 0
