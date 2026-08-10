"""
Overview and detailed analytics using unified Device / PoolStats tables.
Preserves the existing API response shapes for the frontend.
"""
import logging
import math

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.functions import TruncDay, TruncHour
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    PoolStats,
)
from .time_window import parse_int_param as _parse_int_param
from .time_window import parse_time_window

logger = logging.getLogger(__name__)


def _format_difficulty(value):
    if not value or value <= 0:
        return '0'
    value = float(value)
    for unit, div in [('T', 1e12), ('G', 1e9), ('M', 1e6), ('K', 1e3)]:
        if value >= div:
            return f'{value / div:.2f} {unit}'
    return f'{value:.0f}'


def _format_time_duration(hours):
    if hours is None or hours <= 0:
        return 'N/A'
    if hours < 1:
        return f'{hours * 60:.0f} minutes'
    if hours < 24:
        return f'{hours:.1f} hours'
    days = hours / 24
    if days < 30:
        return f'{days:.1f} days'
    return f'{days / 30:.1f} months'


def _make_label(make: str) -> str:
    return {
        Device.MAKE_BITAXE: 'Bitaxe',
        Device.MAKE_AVALON: 'Avalon',
    }.get(make, make.title() if make else 'Unknown')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview_analytics(request):
    """Fleet overview KPIs from unified tables."""
    # Single coherent window (hours + optional absolute from/to)
    window = parse_time_window(request.query_params)
    hours, days = window.hours, window.days
    time_filter = window.as_filter()

    # Enabled for collection (registry flag) — not the same as "online"
    enabled_devices = Device.objects.filter(is_active=True)
    all_devices = Device.objects.all()
    bitaxe_count = enabled_devices.filter(make=Device.MAKE_BITAXE).count()
    avalon_count = enabled_devices.filter(make=Device.MAKE_AVALON).count()
    nmaxe_count = enabled_devices.filter(make=Device.MAKE_NMAXE).count()
    nerdnos_count = enabled_devices.filter(make=Device.MAKE_NERDNOS).count()
    enabled_device_count = enabled_devices.count()
    total_registered = all_devices.count()

    # Online ≈ enabled + recent last_seen + no error (align with frontend ONLINE_MAX_AGE)
    online_cutoff = window.end - timezone.timedelta(minutes=10)
    online_count = enabled_devices.filter(last_seen_at__gte=online_cutoff).filter(
        Q(error_message__isnull=True) | Q(error_message='')
    ).count()

    make_breakdown = list(
        all_devices.values('make').annotate(count=Count('id')).order_by('make')
    )
    devices_by_make = {row['make']: row['count'] for row in make_breakdown}

    # Charts and period KPIs share the same bounds so 1h/6h/custom match the picker
    mining_recent = DeviceMiningStats.objects.filter(**time_filter)
    mining_period = mining_recent
    hardware_recent = DeviceHardwareStats.objects.filter(**time_filter)
    hardware_period = hardware_recent
    pool_stats_recent = (
        PoolStats.objects.filter(**time_filter).order_by('-recorded_at').first()
    )
    pool_stats_period = PoolStats.objects.filter(**time_filter)

    # Backward-compat: active_devices = online count (fleet pulse "X online")
    result = {
        'overview': {
            'active_devices': online_count,
            'online_devices': online_count,
            'enabled_devices': enabled_device_count,
            'total_devices': total_registered,
            'offline_devices': max(0, enabled_device_count - online_count),
            'inactive_devices': max(0, total_registered - enabled_device_count),
            'bitaxe_devices': bitaxe_count,
            'avalon_devices': avalon_count,
            'nmaxe_devices': nmaxe_count,
            'nerdnos_devices': nerdnos_count,
            'devices_by_make': devices_by_make,
            'data_collection_period_hours': hours,
            'analysis_period_days': days,
            'window_start': window.start.isoformat(),
            'window_end': window.end.isoformat(),
            'last_updated': window.end.isoformat(),
        },
        'mining': {'current': {}, 'period': {}, 'efficiency': {}},
        'hardware': {'current': {}, 'period': {}, 'health': {}},
        'pool': {'current': {}, 'performance': {}},
        'financial': {},
        'trends': {},
    }

    current_hashrate_total_ghs = 0.0
    current_shares_accepted = 0
    current_shares_rejected = 0
    for device in enabled_devices:
        latest = DeviceMiningStats.objects.filter(device=device).first()
        if latest:
            current_hashrate_total_ghs += latest.hashrate_ghs or 0
            current_shares_accepted += latest.shares_accepted or 0
            current_shares_rejected += latest.shares_rejected or 0

    best_row = (
        DeviceMiningStats.objects.filter(best_difficulty__isnull=False, best_difficulty__gt=0)
        .order_by('-best_difficulty')
        .values('best_difficulty', 'recorded_at')
        .first()
    )

    result['mining']['current'] = {
        'total_hashrate_ghs': round(current_hashrate_total_ghs, 2),
        'total_hashrate_ths': round(current_hashrate_total_ghs / 1000, 4),
        'total_shares_accepted': current_shares_accepted,
        'total_shares_rejected': current_shares_rejected,
        'rejection_rate': round(
            (current_shares_rejected / (current_shares_accepted + current_shares_rejected) * 100), 2
        ) if (current_shares_accepted + current_shares_rejected) > 0 else 0,
        'acceptance_rate': round(
            (current_shares_accepted / (current_shares_accepted + current_shares_rejected) * 100), 2
        ) if (current_shares_accepted + current_shares_rejected) > 0 else 0,
        'best_share_difficulty': best_row['best_difficulty'] if best_row else None,
        'best_share_timestamp': best_row['recorded_at'].isoformat() if best_row else None,
    }

    mining_agg = mining_period.aggregate(
        avg_hashrate=Avg('hashrate_ghs'),
        max_hashrate=Max('hashrate_ghs'),
        min_hashrate=Min('hashrate_ghs'),
        total_shares_period=Sum('shares_accepted'),
        total_rejected_period=Sum('shares_rejected'),
        data_points=Count('id'),
    )
    # Fleet avg hashrate ≈ sum of per-device latest averages: use sum of max as crude upper bound
    # Prefer summing average hashrate per device for the period
    per_device_avg = (
        mining_period.values('device_id')
        .annotate(avg_hr=Avg('hashrate_ghs'))
        .aggregate(total=Sum('avg_hr'))
    )
    combined_avg_hashrate = per_device_avg['total'] or mining_agg['avg_hashrate'] or 0
    combined_max_hashrate = mining_agg['max_hashrate'] or 0
    combined_min_hashrate = mining_agg['min_hashrate'] or 0
    combined_shares_accepted = mining_agg['total_shares_period'] or 0
    combined_shares_rejected = mining_agg['total_rejected_period'] or 0
    combined_data_points = mining_agg['data_points'] or 0

    period_best = (
        DeviceMiningStats.objects.filter(
            **time_filter,
            best_difficulty__isnull=False,
        )
        .order_by('-best_difficulty')
        .first()
    )


    # Fleet stability from hourly totals (not min/max of every sample — avoids
    # offline zeros and mixed device scales destroying the score).
    hourly_rows = list(
        mining_period.annotate(bucket=TruncHour('recorded_at'))
        .values('bucket')
        .annotate(total=Sum('hashrate_ghs'))
        .order_by('bucket')
    )
    hourly_totals = [float(r['total'] or 0) for r in hourly_rows if (r['total'] or 0) > 0]
    if len(hourly_totals) >= 2:
        avg_hr = sum(hourly_totals) / len(hourly_totals)
        var_hr = sum((t - avg_hr) ** 2 for t in hourly_totals) / len(hourly_totals)
        cv = (var_hr ** 0.5) / avg_hr if avg_hr else 0
        # CV 0 → 100% stable; CV ≥ 0.5 → 0%
        hashrate_stability = max(0.0, min(100.0, round((1.0 - min(cv / 0.5, 1.0)) * 100, 1)))
    elif len(hourly_totals) == 1:
        hashrate_stability = 100.0
    else:
        hashrate_stability = 0.0

    result['mining']['period'] = {
        'avg_hashrate_ghs': round(combined_avg_hashrate, 2),
        'max_hashrate_ghs': round(combined_max_hashrate, 2),
        'min_hashrate_ghs': round(combined_min_hashrate, 2),
        'hashrate_stability': hashrate_stability,
        'total_shares_accepted': combined_shares_accepted,
        'total_shares_rejected': combined_shares_rejected,
        'total_shares': combined_shares_accepted + combined_shares_rejected,
        'data_points': combined_data_points,
        'best_share_difficulty': period_best.best_difficulty if period_best else None,
        'best_share_timestamp': period_best.recorded_at.isoformat() if period_best else None,
    }

    result['mining']['efficiency'] = {
        'shares_per_hour': round(combined_shares_accepted / hours, 1) if hours > 0 else 0,
        'shares_per_day': round(combined_shares_accepted / days, 1) if days > 0 else 0,
        'rejection_rate': round(
            (combined_shares_rejected / (combined_shares_accepted + combined_shares_rejected) * 100), 2
        ) if (combined_shares_accepted + combined_shares_rejected) > 0 else 0,
        'best_share_ever': best_row['best_difficulty'] if best_row else 0,
        'best_share_timestamp': best_row['recorded_at'].isoformat() if best_row else None,
        'avg_efficiency': round(combined_avg_hashrate / enabled_device_count, 2) if enabled_device_count else 0,
    }

    current_temp_total = current_power_total = current_fan_speed_total = 0.0
    current_temp_count = current_power_count = current_fan_speed_count = 0
    for device in enabled_devices:
        hw = DeviceHardwareStats.objects.filter(device=device).first()
        if not hw:
            continue
        if hw.temperature_c is not None:
            current_temp_total += hw.temperature_c
            current_temp_count += 1
        if hw.power_watts is not None:
            current_power_total += hw.power_watts
            current_power_count += 1
        if hw.fan_speed_rpm is not None:
            current_fan_speed_total += hw.fan_speed_rpm
            current_fan_speed_count += 1

    result['hardware']['current'] = {
        'avg_temperature_c': round(current_temp_total / current_temp_count, 1) if current_temp_count else 0,
        'total_power_watts': round(current_power_total, 1),
        'avg_fan_speed_rpm': round(current_fan_speed_total / current_fan_speed_count, 0) if current_fan_speed_count else None,
        'active_devices': current_power_count,
    }

    hw_agg = hardware_period.aggregate(
        avg_temp=Avg('temperature_c'),
        max_temp=Max('temperature_c'),
        min_temp=Min('temperature_c'),
        avg_power=Avg('power_watts'),
        max_power=Max('power_watts'),
        avg_fan_speed=Avg('fan_speed_rpm'),
        max_fan_speed=Max('fan_speed_rpm'),
        data_points=Count('id'),
    )
    result['hardware']['period'] = {
        'avg_temperature_c': round(hw_agg['avg_temp'] or 0, 1),
        'max_temperature_c': round(hw_agg['max_temp'] or 0, 1),
        'min_temperature_c': round(hw_agg['min_temp'] or 0, 1),
        'avg_power_watts': round(hw_agg['avg_power'] or 0, 1),
        'max_power_watts': round(hw_agg['max_power'] or 0, 1),
        'avg_fan_speed_rpm': round(hw_agg['avg_fan_speed'] or 0, 0),
        'max_fan_speed_rpm': round(hw_agg['max_fan_speed'] or 0, 0),
        'data_points': hw_agg['data_points'] or 0,
    }

    max_temp = hw_agg['max_temp'] or 0
    min_temp = hw_agg['min_temp'] or 0
    temp_range = max_temp - min_temp if max_temp else 0
    avg_temp = hw_agg['avg_temp'] or 0
    avg_power = hw_agg['avg_power'] or 0
    result['hardware']['health'] = {
        'temperature_range_c': round(temp_range, 1),
        'temperature_stability': 100 - min(temp_range * 2, 100),
        'thermal_efficiency': round(combined_avg_hashrate / avg_temp, 2) if avg_temp else 0,
        'power_efficiency_gh_per_watt': round(combined_avg_hashrate / avg_power, 2) if avg_power else 0,
    }

    if pool_stats_recent:
        result['pool']['current'] = {
            'hashrate_1m': pool_stats_recent.hashrate_1m_display,
            'hashrate_5m': pool_stats_recent.hashrate_5m_display,
            'hashrate_1hr': pool_stats_recent.hashrate_1h_display,
            'hashrate_1d': pool_stats_recent.hashrate_1d_display,
            'hashrate_ghs': round(pool_stats_recent.hashrate_1m_ghs or 0, 2),
            'pool_hashrate_ghs': round(pool_stats_recent.hashrate_1m_ghs or 0, 2),
            'total_shares': pool_stats_recent.shares or 0,
            'best_share': pool_stats_recent.best_share or 0,
            'workers': pool_stats_recent.workers or 0,
            'workers_active': pool_stats_recent.workers or 0,
            'network_difficulty': 95000000000000,
        }

    pool_agg = pool_stats_period.aggregate(
        avg_hashrate=Avg('hashrate_1m_ghs'),
        max_hashrate=Max('hashrate_1m_ghs'),
        avg_workers=Avg('workers'),
        max_best_share=Max('best_share'),
    )
    stale_rate = 0.0
    if (combined_shares_accepted + combined_shares_rejected) > 0:
        stale_rate = (combined_shares_rejected / (combined_shares_accepted + combined_shares_rejected)) * 100

    result['pool']['performance'] = {
        'avg_hashrate_ghs': round(pool_agg['avg_hashrate'] or 0, 2),
        'max_hashrate_ghs': round(pool_agg['max_hashrate'] or 0, 2),
        'avg_workers': round(pool_agg['avg_workers'] or 0, 1),
        'best_share_period': pool_agg['max_best_share'] or 0,
        'stale_rate': round(stale_rate, 1),
    }

    btc_block_reward = 3.125
    network_hashrate_ehs = 650
    btc_price_usd = 67000
    network_hashrate_ghs = network_hashrate_ehs * 1e9
    pool_percentage = (current_hashrate_total_ghs / network_hashrate_ghs) * 100 if network_hashrate_ghs else 0
    blocks_per_day = 144
    expected_btc_per_day = (current_hashrate_total_ghs / network_hashrate_ghs) * blocks_per_day * btc_block_reward if network_hashrate_ghs else 0
    kwh_price = 0.12
    energy_consumption_kwh_per_day = (current_power_total / 1000) * 24
    energy_cost_per_day = energy_consumption_kwh_per_day * kwh_price

    result['financial'] = {
        'network_percentage': f"{pool_percentage:.10f}",
        'expected_btc_per_day': f"{expected_btc_per_day:.10f}",
        'expected_usd_per_day': round(expected_btc_per_day * btc_price_usd, 2),
        'expected_btc_per_month': f"{expected_btc_per_day * 30:.10f}",
        'expected_usd_per_month': round(expected_btc_per_day * 30 * btc_price_usd, 2),
        'energy_cost_per_day_usd': round(energy_cost_per_day, 2),
        'energy_cost_per_month_usd': round(energy_cost_per_day * 30, 2),
        'net_profit_per_day_usd': round((expected_btc_per_day * btc_price_usd) - energy_cost_per_day, 2),
        'net_profit_per_month_usd': round(((expected_btc_per_day * btc_price_usd) - energy_cost_per_day) * 30, 2),
        'roi_years': (
            round(1500 / (((expected_btc_per_day * btc_price_usd) - energy_cost_per_day) * 365), 2)
            if (expected_btc_per_day * btc_price_usd) > energy_cost_per_day
            and ((expected_btc_per_day * btc_price_usd) - energy_cost_per_day) > 0
            else None
        ),
        'assumptions': {
            'btc_price_usd': btc_price_usd,
            'network_hashrate_ehs': network_hashrate_ehs,
            'kwh_price_usd': kwh_price,
            'device_cost_usd': 1500,
        },
    }

    # Trends: sum hashrate by hour across devices
    hourly_mining_raw = (
        mining_recent.annotate(hour=TruncHour('recorded_at'))
        .values('hour')
        .annotate(avg_hashrate=Avg('hashrate_ghs'), total_shares=Sum('shares_accepted'))
        .order_by('hour')
    )
    # Better fleet HR: sum of avg hashrate per device per hour
    per_dev_hour = (
        mining_recent.annotate(hour=TruncHour('recorded_at'))
        .values('hour', 'device_id')
        .annotate(avg_hr=Avg('hashrate_ghs'), shares=Sum('shares_accepted'))
    )
    combined_hourly_mining = {}
    for item in per_dev_hour:
        hour_key = item['hour'].isoformat()
        bucket = combined_hourly_mining.setdefault(
            hour_key, {'hour': hour_key, 'hashrate_ghs': 0, 'shares': 0}
        )
        bucket['hashrate_ghs'] += item['avg_hr'] or 0
        bucket['shares'] += item['shares'] or 0

    hourly_hw = (
        hardware_recent.annotate(hour=TruncHour('recorded_at'))
        .values('hour')
        .annotate(avg_temp=Avg('temperature_c'), avg_power=Avg('power_watts'), power_sum=Sum('power_watts'))
        .order_by('hour')
    )
    # power as sum of per-device averages per hour
    per_dev_hw_hour = (
        hardware_recent.annotate(hour=TruncHour('recorded_at'))
        .values('hour', 'device_id')
        .annotate(avg_temp=Avg('temperature_c'), avg_power=Avg('power_watts'))
    )
    combined_hourly_hardware = {}
    for item in per_dev_hw_hour:
        hour_key = item['hour'].isoformat()
        if hour_key not in combined_hourly_hardware:
            combined_hourly_hardware[hour_key] = {
                'hour': hour_key,
                'temperature_c': item['avg_temp'] or 0,
                'power_watts': item['avg_power'] or 0,
                'device_count': 1,
            }
        else:
            old = combined_hourly_hardware[hour_key]
            n = old['device_count']
            old['temperature_c'] = (old['temperature_c'] * n + (item['avg_temp'] or 0)) / (n + 1)
            old['power_watts'] += item['avg_power'] or 0
            old['device_count'] = n + 1

    # Best shares by make for chart series
    combined_hourly_best_shares = {}
    for hour_key in combined_hourly_mining:
        combined_hourly_best_shares[hour_key] = {
            'hour': hour_key,
            'bitaxe_best_share': 0,
            'bitaxe_device_name': None,
            'avalon_best_share': 0,
            'avalon_device_name': None,
            'hashrate_ghs': combined_hourly_mining[hour_key].get('hashrate_ghs', 0),
        }

    for make, share_key, name_key in (
        (Device.MAKE_BITAXE, 'bitaxe_best_share', 'bitaxe_device_name'),
        (Device.MAKE_AVALON, 'avalon_best_share', 'avalon_device_name'),
    ):
        rows = (
            mining_recent.filter(device__make=make, best_difficulty__isnull=False)
            .annotate(hour=TruncHour('recorded_at'))
            .values('hour')
            .annotate(best_share_difficulty=Max('best_difficulty'), device_name=Max('device__name'))
            .order_by('hour')
        )
        for item in rows:
            hour_key = item['hour'].isoformat()
            if hour_key not in combined_hourly_best_shares:
                combined_hourly_best_shares[hour_key] = {
                    'hour': hour_key,
                    'bitaxe_best_share': 0,
                    'bitaxe_device_name': None,
                    'avalon_best_share': 0,
                    'avalon_device_name': None,
                    'hashrate_ghs': combined_hourly_mining.get(hour_key, {}).get('hashrate_ghs', 0),
                }
            combined_hourly_best_shares[hour_key][share_key] = item['best_share_difficulty'] or 0
            combined_hourly_best_shares[hour_key][name_key] = item['device_name'] or 'Unknown'

    result['trends'] = {
        'hourly_hashrate': [
            {
                'hour': data['hour'],
                'hashrate_ghs': round(data['hashrate_ghs'], 2),
                'shares': data['shares'],
            }
            for data in sorted(combined_hourly_mining.values(), key=lambda x: x['hour'])
        ],
        'hourly_hardware': [
            {
                'hour': data['hour'],
                'temperature_c': round(data['temperature_c'], 1),
                'power_watts': round(data['power_watts'], 1),
            }
            for data in sorted(combined_hourly_hardware.values(), key=lambda x: x['hour'])
        ],
        'hourly_best_shares': [
            {
                'hour': data['hour'],
                'bitaxe_best_share': data['bitaxe_best_share'],
                'bitaxe_device_name': data['bitaxe_device_name'],
                'avalon_best_share': data['avalon_best_share'],
                'avalon_device_name': data['avalon_device_name'],
                'hashrate_ghs': round(data['hashrate_ghs'], 2),
            }
            for data in sorted(combined_hourly_best_shares.values(), key=lambda x: x['hour'])
        ],
    }

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detailed_analytics(request):
    """Analytics dashboard data from unified tables."""
    window = parse_time_window(request.query_params)
    hours, days = window.hours, window.days
    time_filter = window.as_filter()

    active_devices = Device.objects.filter(is_active=True)

    result = {
        'energy_analysis': {},
        'best_difficulty_prediction': {},
        'historical_best_shares': {},
        'device_comparison': {},
        'cost_analysis': {},
        'efficiency_trends': [],
        'predictions': {},
    }

    current_power_total = 0.0
    device_power_data = []
    for device in active_devices:
        latest_hw = DeviceHardwareStats.objects.filter(device=device).first()
        latest_mining = DeviceMiningStats.objects.filter(device=device).first()
        if latest_hw:
            power = latest_hw.power_watts or 0
            hashrate = latest_mining.hashrate_ghs if latest_mining else 0
            current_power_total += power
            device_power_data.append({
                'device_name': device.name,
                'device_type': _make_label(device.make),
                'power_watts': round(power, 1),
                'hashrate_ghs': round(hashrate, 2),
                'efficiency_w_per_gh': round(power / hashrate, 2) if hashrate > 0 else 0,
                'efficiency_j_per_th': round((power / hashrate) * 1000, 2) if hashrate > 0 else 0,
            })

    per_dev_hw_hour = (
        DeviceHardwareStats.objects.filter(**time_filter)
        .annotate(hour=TruncHour('recorded_at'))
        .values('hour', 'device_id')
        .annotate(avg_power=Avg('power_watts'), avg_temp=Avg('temperature_c'))
    )
    power_by_hour = {}
    for item in per_dev_hw_hour:
        hour_key = item['hour'].isoformat()
        if hour_key not in power_by_hour:
            power_by_hour[hour_key] = {
                'hour': hour_key,
                'power_watts': item['avg_power'] or 0,
                'temperature_c': item['avg_temp'] or 0,
                'n': 1,
            }
        else:
            b = power_by_hour[hour_key]
            b['power_watts'] += item['avg_power'] or 0
            b['temperature_c'] = (b['temperature_c'] * b['n'] + (item['avg_temp'] or 0)) / (b['n'] + 1)
            b['n'] += 1

    result['energy_analysis'] = {
        'current_power_watts': round(current_power_total, 1),
        'current_power_kw': round(current_power_total / 1000, 3),
        'devices': sorted(device_power_data, key=lambda x: x['power_watts'], reverse=True),
        'power_trend': [
            {
                'hour': v['hour'],
                'power_watts': v['power_watts'],
                'temperature_c': v['temperature_c'],
            }
            for v in sorted(power_by_hour.values(), key=lambda x: x['hour'])
        ],
    }

    total_hashrate_ghs = sum(d['hashrate_ghs'] for d in device_power_data)
    total_hashrate_hs = total_hashrate_ghs * 1e9

    all_time_best = (
        DeviceMiningStats.objects.filter(best_difficulty__isnull=False, best_difficulty__gt=0)
        .select_related('device')
        .order_by('-best_difficulty')
        .first()
    )
    all_time_best_difficulty = int(all_time_best.best_difficulty) if all_time_best and all_time_best.best_difficulty else 0
    all_time_best_source = _make_label(all_time_best.device.make) if all_time_best else None

    if total_hashrate_hs > 0 and all_time_best_difficulty > 0:
        TWO_POW_32 = 4294967296
        expected_seconds = (all_time_best_difficulty * TWO_POW_32) / total_hashrate_hs
        expected_hours = expected_seconds / 3600
        expected_days = expected_hours / 24
        lambda_rate = total_hashrate_hs / (all_time_best_difficulty * TWO_POW_32)
        prob_beat_1h = min(max(1 - math.exp(-3600 * lambda_rate), 0), 1)
        prob_beat_24h = min(max(1 - math.exp(-86400 * lambda_rate), 0), 1)
        prob_beat_7d = min(max(1 - math.exp(-604800 * lambda_rate), 0), 1)
    else:
        expected_hours = expected_days = 0
        prob_beat_1h = prob_beat_24h = prob_beat_7d = 0

    recent_bests = (
        DeviceMiningStats.objects.filter(**time_filter)
        .filter(
            Q(best_difficulty__isnull=False, best_difficulty__gt=0)
            | Q(best_session_difficulty__isnull=False, best_session_difficulty__gt=0)
        )
        .annotate(day=TruncDay('recorded_at'))
        .values('day', 'device__make', 'device__name')
        .annotate(
            max_best_ever=Max('best_difficulty'),
            max_best_session=Max('best_session_difficulty'),
        )
        .order_by('day')
    )
    daily_bests = {}
    for item in recent_bests:
        day_key = item['day'].isoformat()
        make_label = _make_label(item['device__make'])
        best_ever = item['max_best_ever'] or 0
        best_session = item['max_best_session'] or best_ever
        if day_key not in daily_bests or best_ever > daily_bests[day_key]['best_difficulty']:
            daily_bests[day_key] = {
                'date': day_key,
                'best_difficulty': best_ever,
                'best_session_difficulty': best_session,
                'device_name': item['device__name'],
                'device_type': make_label,
            }
        elif day_key in daily_bests and best_session > daily_bests[day_key].get('best_session_difficulty', 0):
            daily_bests[day_key]['best_session_difficulty'] = best_session

    result['best_difficulty_prediction'] = {
        'current_hashrate_ghs': round(total_hashrate_ghs, 2),
        'current_hashrate_ths': round(total_hashrate_ghs / 1000, 4),
        'all_time_best_difficulty': all_time_best_difficulty,
        'all_time_best_formatted': _format_difficulty(all_time_best_difficulty),
        'all_time_best_timestamp': all_time_best.recorded_at.isoformat() if all_time_best else None,
        'expected_time_to_beat': {
            'hours': round(expected_hours, 1),
            'days': round(expected_days, 1),
            'formatted': _format_time_duration(expected_hours),
        },
        'probability_to_beat_current_best': {
            '1_hour': round(prob_beat_1h * 100, 4),
            '24_hours': round(prob_beat_24h * 100, 4),
            '7_days': round(prob_beat_7d * 100, 4),
        },
        'expected_best_difficulty': {
            '1_day': 0,
            '7_days': 0,
            '30_days': 0,
            '1_day_formatted': '0',
            '7_days_formatted': '0',
            '30_days_formatted': '0',
        },
        'daily_best_shares': sorted(daily_bests.values(), key=lambda x: x['date']),
    }

    unique_bests = (
        DeviceMiningStats.objects.filter(best_difficulty__isnull=False, best_difficulty__gt=0)
        .values('device__name', 'device__make', 'best_difficulty')
        .annotate(first_timestamp=Min('recorded_at'), hashrate=Avg('hashrate_ghs'))
        .order_by('-best_difficulty')[:40]
    )
    top_shares = []
    seen = set()
    for share in unique_bests:
        key = (share['device__name'], share['best_difficulty'])
        if key in seen:
            continue
        seen.add(key)
        top_shares.append({
            'difficulty': share['best_difficulty'],
            'difficulty_formatted': _format_difficulty(share['best_difficulty']),
            'device_name': share['device__name'],
            'device_type': _make_label(share['device__make']),
            'timestamp': share['first_timestamp'].isoformat() if share['first_timestamp'] else None,
            'hashrate_at_time': round(share['hashrate'] or 0, 2),
        })
    top_shares = sorted(top_shares, key=lambda x: x['difficulty'], reverse=True)[:10]

    result['historical_best_shares'] = {
        'top_10': top_shares,
        'total_records_bitaxe': DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_BITAXE, best_difficulty__gt=0
        ).count(),
        'total_records_avalon': DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_AVALON, best_difficulty__gt=0
        ).count(),
    }

    settings = CollectorSettings.get_settings()
    kwh_price = float(settings.energy_rate)
    energy_currency = settings.energy_currency
    show_revenue = settings.show_revenue_stats
    btc_price = float(settings.cached_btc_price)
    network_hashrate_ehs = float(settings.cached_network_hashrate)
    network_difficulty = float(settings.cached_network_difficulty)
    network_data_updated = settings.network_data_updated_at

    power_kw = current_power_total / 1000
    daily_kwh = power_kw * 24
    monthly_kwh = daily_kwh * 30
    yearly_kwh = daily_kwh * 365
    daily_cost = daily_kwh * kwh_price
    monthly_cost = monthly_kwh * kwh_price
    yearly_cost = yearly_kwh * kwh_price

    btc_per_block = 3.125
    blocks_per_day = 144
    if show_revenue and network_hashrate_ehs > 0:
        network_hashrate_ghs = network_hashrate_ehs * 1e9
        daily_btc = (total_hashrate_ghs / network_hashrate_ghs) * blocks_per_day * btc_per_block
        monthly_btc = daily_btc * 30
        yearly_btc = daily_btc * 365
        daily_revenue = daily_btc * btc_price
        monthly_revenue = monthly_btc * btc_price
        yearly_revenue = yearly_btc * btc_price
    else:
        daily_btc = monthly_btc = yearly_btc = 0
        daily_revenue = monthly_revenue = yearly_revenue = 0

    result['cost_analysis'] = {
        'settings': {
            'energy_rate': kwh_price,
            'energy_currency': energy_currency,
            'show_revenue_stats': show_revenue,
        },
        'network_data': {
            'btc_price': btc_price,
            'network_hashrate_ehs': network_hashrate_ehs,
            'network_difficulty': network_difficulty,
            'updated_at': network_data_updated.isoformat() if network_data_updated else None,
        },
        'energy_consumption': {
            'current_power_watts': round(current_power_total, 1),
            'current_power_kw': round(power_kw, 3),
            'daily_kwh': round(daily_kwh, 2),
            'monthly_kwh': round(monthly_kwh, 2),
            'yearly_kwh': round(yearly_kwh, 2),
        },
        'energy_costs': {
            'kwh_price': kwh_price,
            'currency': energy_currency,
            'daily_cost': round(daily_cost, 2),
            'monthly_cost': round(monthly_cost, 2),
            'yearly_cost': round(yearly_cost, 2),
        },
    }
    if show_revenue:
        result['cost_analysis']['mining_revenue'] = {
            'btc_price': btc_price,
            'daily_btc': f"{daily_btc:.10f}",
            'monthly_btc': f"{monthly_btc:.10f}",
            'yearly_btc': f"{yearly_btc:.10f}",
            'daily_revenue': round(daily_revenue, 4),
            'monthly_revenue': round(monthly_revenue, 4),
            'yearly_revenue': round(yearly_revenue, 4),
        }
        result['cost_analysis']['profitability'] = {
            'daily_profit': round(daily_revenue - daily_cost, 4),
            'monthly_profit': round(monthly_revenue - monthly_cost, 4),
            'yearly_profit': round(yearly_revenue - yearly_cost, 4),
            'is_profitable': daily_revenue > daily_cost,
            'break_even_btc_price': round(daily_cost / daily_btc, 2) if daily_btc > 0 else None,
        }
        result['cost_analysis']['efficiency_metrics'] = {
            'cost_per_gh_per_day': round(daily_cost / total_hashrate_ghs, 4) if total_hashrate_ghs > 0 else 0,
            'btc_per_kwh': f"{daily_btc / daily_kwh:.12f}" if daily_kwh > 0 else "0",
            'sats_per_kwh': round((daily_btc * 100000000) / daily_kwh, 4) if daily_kwh > 0 else 0,
        }
        result['cost_analysis']['assumptions'] = {
            'network_hashrate_ehs': network_hashrate_ehs,
            'btc_per_block': btc_per_block,
            'blocks_per_day': blocks_per_day,
        }

    device_stats = []
    for device in active_devices:
        latest_mining = DeviceMiningStats.objects.filter(device=device).first()
        latest_hw = DeviceHardwareStats.objects.filter(device=device).first()
        device_best = (
            DeviceMiningStats.objects.filter(device=device, best_difficulty__isnull=False, best_difficulty__gt=0)
            .order_by('-best_difficulty')
            .first()
        )
        if latest_mining and latest_hw:
            device_stats.append({
                'device_name': device.name,
                'device_type': _make_label(device.make),
                'hashrate_ghs': round(latest_mining.hashrate_ghs or 0, 2),
                'power_watts': round(latest_hw.power_watts or 0, 1),
                'temperature_c': round(latest_hw.temperature_c or 0, 1),
                'efficiency_j_per_th': round(latest_hw.efficiency_j_per_th or 0, 2),
                'best_difficulty': device_best.best_difficulty if device_best else 0,
                'best_difficulty_formatted': _format_difficulty(device_best.best_difficulty) if device_best else '0',
                'uptime_hours': round((latest_mining.uptime_seconds or 0) / 3600, 1),
                'shares_accepted': latest_mining.shares_accepted or 0,
                'shares_rejected': latest_mining.shares_rejected or 0,
            })

    result['device_comparison'] = {
        'devices': sorted(device_stats, key=lambda x: x['hashrate_ghs'], reverse=True),
        'total_devices': len(device_stats),
    }

    daily_efficiency = (
        DeviceHardwareStats.objects.filter(**time_filter)
        .annotate(day=TruncDay('recorded_at'))
        .values('day')
        .annotate(
            avg_efficiency=Avg('efficiency_j_per_th'),
            avg_power=Avg('power_watts'),
            avg_temp=Avg('temperature_c'),
        )
        .order_by('day')
    )
    result['efficiency_trends'] = [
        {
            'date': item['day'].isoformat(),
            'avg_efficiency_j_per_th': round(item['avg_efficiency'] or 0, 2),
            'avg_power_watts': round(item['avg_power'] or 0, 1),
            'avg_temperature_c': round(item['avg_temp'] or 0, 1),
        }
        for item in daily_efficiency
    ]

    result['predictions'] = {
        'all_time_best_source': all_time_best_source,
    }

    return Response(result)
