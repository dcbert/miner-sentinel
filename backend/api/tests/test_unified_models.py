"""Tests for unified Device / PoolStats models."""
import pytest
from django.db import IntegrityError
from django.utils import timezone

from api.models import (
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)


@pytest.mark.django_db
class TestDeviceModel:
    def test_same_device_id_allowed_across_makes(self):
        Device.objects.create(
            device_id='miner-1',
            name='Bitaxe One',
            make=Device.MAKE_BITAXE,
            protocol=Device.PROTOCOL_HTTP_AXEOS,
            ip_address='192.168.1.10',
        )
        Device.objects.create(
            device_id='miner-1',
            name='Avalon One',
            make=Device.MAKE_AVALON,
            protocol=Device.PROTOCOL_CGMINER_TCP,
            ip_address='192.168.1.20',
            port=4028,
        )
        assert Device.objects.filter(device_id='miner-1').count() == 2

    def test_duplicate_make_device_id_rejected(self):
        Device.objects.create(
            device_id='miner-1',
            name='Bitaxe One',
            make=Device.MAKE_BITAXE,
            protocol=Device.PROTOCOL_HTTP_AXEOS,
            ip_address='192.168.1.10',
        )
        with pytest.raises(IntegrityError):
            Device.objects.create(
                device_id='miner-1',
                name='Duplicate',
                make=Device.MAKE_BITAXE,
                protocol=Device.PROTOCOL_HTTP_AXEOS,
                ip_address='192.168.1.11',
            )

    def test_mining_stats_cascade_delete(self):
        device = Device.objects.create(
            device_id='bx-1',
            name='BX',
            make=Device.MAKE_BITAXE,
            protocol=Device.PROTOCOL_HTTP_AXEOS,
            ip_address='10.0.0.1',
        )
        DeviceMiningStats.objects.create(
            device=device,
            recorded_at=timezone.now(),
            hashrate_ghs=100.0,
            shares_accepted=1,
            shares_rejected=0,
            uptime_seconds=60,
        )
        assert DeviceMiningStats.objects.count() == 1
        device.delete()
        assert DeviceMiningStats.objects.count() == 0

    def test_hardware_and_system_create(self):
        device = Device.objects.create(
            device_id='bx-2',
            name='BX2',
            make=Device.MAKE_BITAXE,
            protocol=Device.PROTOCOL_HTTP_AXEOS,
            ip_address='10.0.0.2',
        )
        now = timezone.now()
        DeviceHardwareStats.objects.create(
            device=device,
            recorded_at=now,
            temperature_c=55.0,
            power_watts=20.0,
            efficiency_j_per_th=40.0,
        )
        DeviceSystemInfo.objects.create(
            device=device,
            recorded_at=now,
            hostname='bitaxe',
            firmware_version='1.0',
            details={'asic_model': 'BM1366', 'free_heap': 1000},
        )
        sysinfo = DeviceSystemInfo.objects.get(device=device)
        assert sysinfo.details['asic_model'] == 'BM1366'


@pytest.mark.django_db
class TestPoolStatsModel:
    def test_create_ckpool_and_publicpool_rows(self):
        now = timezone.now()
        PoolStats.objects.create(
            pool_type=PoolStats.POOL_CKPOOL,
            pool_address='bc1qtest',
            recorded_at=now,
            hashrate_1m_ghs=466.0,
            hashrate_1m_display='466G',
            workers=2,
            best_share=1e12,
        )
        PoolStats.objects.create(
            pool_type=PoolStats.POOL_PUBLICPOOL,
            pool_address='bc1qtest',
            recorded_at=now,
            hashrate_1m_ghs=100.0,
            workers=1,
            details={'workers': []},
        )
        assert PoolStats.objects.count() == 2
        assert PoolStats.objects.filter(pool_type='ckpool').count() == 1

    def test_filter_by_pool_type_and_address(self):
        now = timezone.now()
        PoolStats.objects.create(
            pool_type='ckpool',
            pool_address='addr-a',
            recorded_at=now,
            hashrate_1m_ghs=1.0,
        )
        PoolStats.objects.create(
            pool_type='publicpool',
            pool_address='addr-b',
            recorded_at=now,
            hashrate_1m_ghs=2.0,
        )
        qs = PoolStats.objects.filter(pool_type='ckpool', pool_address='addr-a')
        assert qs.count() == 1
        assert qs.first().hashrate_1m_ghs == 1.0
