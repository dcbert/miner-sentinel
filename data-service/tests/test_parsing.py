#!/usr/bin/env python3
"""
Test the Avalon collector parsing functions with real device data
"""

import os
import sys
from pathlib import Path

# Portable path setup: add data-service root so "from collectors..." and "from notifications..." work
# regardless of cwd, invocation dir, or CI environment. Fixes previous hardcoded /Users/... path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.avalon_collector import AvalonCollector


def test_parsing():
    """Test the parsing functions with sample data from your device."""

    # Sample data from the actual device response
    stats_info = {
        'MM ID0': 'Ver[Nano3s-25021401_56abae7] LVer[25021401_56abae7] BVer[25021401_56abae7] FW[Release] LED[0-0] LEDUser[0-100-100-5-0-255] LcdOnoff[1] LcdSwitch[2] DNA[02010000bd448216] MEMFREE[63728] PFCnt[0] NETFAIL[0 0 0 0 0 0 0 0] SYSTEMSTATU[Work: In Work, Hash Board: 1] Elapsed[10027] BOOTBY[0x01.00000000] LW[7753951] MH[0] DHW[0] HW[0] DH[2.374%] ITemp[-273] OTemp[65] TMax[95] TAvg[90] TarT[90] Fan1[1520] FanR[33%] PS[0 0 27541 4 0 3756 133] GHSspd[6598.84] DHspd[2.374%] GHSmm[6783.65] GHSavg[6695.18] WU[93530.53] Freq[464.89] MGHS[6695.18] MTmax[95] MTavg[90] TA[12] Core[A3197S] BIN[60] PING[78] SoftOFF[0] ECHU[0] ECMM[0] PLL0[499 254 423 648] SF0[432 450 471 492] PVT_T0[ 85  91  91  91  91  90  85  86  95  95  91  87] PVT_V0[299 303 301 303 300 301 306 301 297 296 303 305] MW0[321 338 337 334 296 338 294 322 309 283 318 321] CRC[0] COMCRC[0] ATA2[133-90-3756-432-20] WORKMODE[2] WORKLEVEL[0] MPO[133] CALIALL[7] ADJ[1]'
    }

    summary_info = {
        'MHS av': '6676358.98',
        'Accepted': '2547',
        'Rejected': '10',
        'Elapsed': '10010',
        'Best Share': '12031286'
    }

    version_info = {
        'PROD': 'Avalon Nano3s',
        'MODEL': 'Nano3s',
        'CGMiner': '4.11.1',
        'MAC': 'e0e1a93f8523',
        'DNA': '02010000bd448216'
    }

    # Create a collector instance (we won't use database features, just parsing).
    # Updated for new AvalonCollector(database_url) signature.
    collector = AvalonCollector("postgresql://test:test@localhost:5432/test")  # dummy URL for parsing-only test

    # Test hashrate parsing
    hashrate = collector._parse_hashrate_mhs(summary_info.get('MHS av', '0'))
    assert hashrate > 0, "Hashrate should be positive"
    assert abs(hashrate - 6676.36) < 1.0, f"Expected ~6676 GH/s, got {hashrate}"

    # Test temperature parsing
    temperature = collector._parse_temperature_from_stats(stats_info)
    assert temperature > 0, "Temperature should be positive"
    assert temperature == 65, f"Expected 65°C (from OTemp[65]), got {temperature}"

    # Test power parsing
    power = collector._parse_power_from_stats(stats_info)
    assert power > 0, "Power should be positive"

    # Test fan speed parsing
    fan_speed = collector._parse_fan_speed_from_stats(stats_info)
    assert fan_speed >= 0, "Fan speed should be non-negative"

    # Test frequency parsing
    frequency = collector._parse_frequency_from_stats(stats_info)
    assert frequency > 0, "Frequency should be positive"

    # Test voltage parsing
    voltage = collector._parse_voltage_from_stats(stats_info)
    assert voltage >= 0, "Voltage should be non-negative"

    # Test memory usage parsing
    memory_usage = collector._parse_memory_usage_from_stats(stats_info)
    assert 0 <= memory_usage <= 100, f"Memory usage should be 0-100%, got {memory_usage}"

    # Efficiency sanity check
    efficiency = (power / (hashrate / 1000.0)) if hashrate > 0 else 0
    assert efficiency > 0, "Efficiency should be positive"

if __name__ == "__main__":
    test_parsing()