import logging
from datetime import timedelta

import pandas as pd
from django.contrib.auth import authenticate, login, logout
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
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
)
from .serializers import (
    AvalonDeviceSerializer,
    AvalonDeviceWriteSerializer,
    BitAxeDeviceSerializer,
    BitAxeDeviceWriteSerializer,
    BitAxeHardwareLogSerializer,
    BitAxeMiningStatsSerializer,
    BitAxePoolStatsSerializer,
    BitAxeSystemInfoSerializer,
    CollectorSettingsSerializer,
)

logger = logging.getLogger(__name__)


class BitAxeDeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Bitaxe devices with full CRUD operations.
    """
    queryset = BitAxeDevice.objects.all()
    serializer_class = BitAxeDeviceSerializer
    lookup_field = 'device_id'  # Use device_id instead of database pk

    def get_queryset(self):
        """Optionally filter to only active devices."""
        queryset = super().get_queryset()
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_serializer_class(self):
        """Use write serializer for create/update operations."""
        if self.action in ['create', 'update', 'partial_update']:
            return BitAxeDeviceWriteSerializer
        return BitAxeDeviceSerializer


class BitAxeMiningStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Bitaxe mining statistics.
    """
    queryset = BitAxeMiningStats.objects.all()
    serializer_class = BitAxeMiningStatsSerializer

    def get_queryset(self):
        """Filter by device if specified."""
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest mining stats for all devices."""
        devices = BitAxeDevice.objects.filter(is_active=True)
        results = []

        for device in devices:
            latest_stat = BitAxeMiningStats.objects.filter(device=device).first()
            if latest_stat:
                serializer = self.get_serializer(latest_stat)
                results.append(serializer.data)

        return Response(results)

    @action(detail=False, methods=['get'])
    def hashrate_trend(self, request):
        """Get hashrate trend over time."""
        device_id = request.query_params.get('device_id')
        hours = int(request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)

        queryset = BitAxeMiningStats.objects.filter(recorded_at__gte=start_time)

        if device_id:
            queryset = queryset.filter(device__device_id=device_id)

        stats = queryset.values(
            'device__device_name', 'recorded_at', 'hashrate_ghs',
            'shares_accepted', 'shares_rejected'
        ).order_by('recorded_at')

        return Response(list(stats))


class BitAxeHardwareLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Bitaxe hardware logs.
    """
    queryset = BitAxeHardwareLog.objects.all()
    serializer_class = BitAxeHardwareLogSerializer

    def get_queryset(self):
        """Filter by device if specified."""
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest hardware stats for all devices."""
        devices = BitAxeDevice.objects.filter(is_active=True)
        results = []

        for device in devices:
            latest_log = BitAxeHardwareLog.objects.filter(device=device).first()
            if latest_log:
                serializer = self.get_serializer(latest_log)
                results.append(serializer.data)

        return Response(results)

    @action(detail=False, methods=['get'])
    def temperature_trend(self, request):
        """Get temperature and power trend over time."""
        device_id = request.query_params.get('device_id')
        hours = int(request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)

        queryset = BitAxeHardwareLog.objects.filter(recorded_at__gte=start_time)

        if device_id:
            queryset = queryset.filter(device__device_id=device_id)

        logs = queryset.values(
            'device__device_name', 'recorded_at', 'temperature_c',
            'power_watts', 'fan_speed_rpm'
        ).order_by('recorded_at')

        return Response(list(logs))


class BitAxeSystemInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Bitaxe system information.
    """
    queryset = BitAxeSystemInfo.objects.all()
    serializer_class = BitAxeSystemInfoSerializer

    def get_queryset(self):
        """Filter by device if specified."""
        queryset = super().get_queryset()
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=False, methods=['get'], url_path='device/(?P<device_id>[^/.]+)')
    def device_details(self, request, device_id=None):
        """Get complete device details including latest stats, hardware, and system info."""
        try:
            device = BitAxeDevice.objects.get(device_id=device_id)
        except BitAxeDevice.DoesNotExist:
            return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get latest data from all tables
        latest_mining = BitAxeMiningStats.objects.filter(device=device).first()
        latest_hardware = BitAxeHardwareLog.objects.filter(device=device).first()
        latest_system = BitAxeSystemInfo.objects.filter(device=device).first()

        # Get trends (last 24 hours)
        start_time = timezone.now() - timedelta(hours=24)
        hashrate_trend = BitAxeMiningStats.objects.filter(
            device=device,
            recorded_at__gte=start_time
        ).values('recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected').order_by('recorded_at')

        temp_trend = BitAxeHardwareLog.objects.filter(
            device=device,
            recorded_at__gte=start_time
        ).values('recorded_at', 'temperature_c', 'power_watts', 'fan_speed_rpm').order_by('recorded_at')

        return Response({
            'device': BitAxeDeviceSerializer(device).data,
            'latest_mining': BitAxeMiningStatsSerializer(latest_mining).data if latest_mining else None,
            'latest_hardware': BitAxeHardwareLogSerializer(latest_hardware).data if latest_hardware else None,
            'latest_system': BitAxeSystemInfoSerializer(latest_system).data if latest_system else None,
            'hashrate_trend_24h': list(hashrate_trend),
            'temperature_trend_24h': list(temp_trend),
        })


class BitAxePoolStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Bitaxe pool statistics from CKPool.
    """
    queryset = BitAxePoolStats.objects.all()
    serializer_class = BitAxePoolStatsSerializer

    def get_queryset(self):
        """Filter by pool address if provided."""
        queryset = super().get_queryset()
        pool_address = self.request.query_params.get('pool_address')
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get the most recent pool statistics."""
        pool_address = request.query_params.get('pool_address')

        if pool_address:
            latest_stat = BitAxePoolStats.objects.filter(pool_address=pool_address).first()
        else:
            latest_stat = BitAxePoolStats.objects.first()

        if latest_stat:
            serializer = self.get_serializer(latest_stat)
            return Response(serializer.data)
        return Response({'detail': 'No pool statistics found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def hashrate_trend(self, request):
        """Get hashrate trend over time."""
        pool_address = request.query_params.get('pool_address')
        hours = int(request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)

        queryset = BitAxePoolStats.objects.filter(recorded_at__gte=start_time)
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)

        stats = queryset.values(
            'recorded_at', 'hashrate_1m', 'hashrate_5m', 'hashrate_1hr',
            'hashrate_1d', 'hashrate_1m_ghs', 'shares', 'workers'
        ).order_by('recorded_at')

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get aggregated pool statistics."""
        pool_address = request.query_params.get('pool_address')
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        queryset = BitAxePoolStats.objects.filter(recorded_at__gte=start_date)
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)

        if not queryset.exists():
            return Response({
                'total_shares': 0,
                'avg_workers': 0,
                'max_hashrate_ghs': 0,
                'best_share': 0,
                'data_points': 0,
            })

        stats = queryset.aggregate(
            latest_shares=Max('shares'),
            avg_workers=Avg('workers'),
            max_hashrate_ghs=Max('hashrate_1m_ghs'),
            best_share=Max('bestshare'),
            data_points=Count('id')
        )

        # Get first record to calculate total shares
        first_record = queryset.order_by('recorded_at').first()
        latest_record = queryset.order_by('-recorded_at').first()

        if first_record and latest_record:
            stats['total_shares'] = latest_record.shares - first_record.shares
        else:
            stats['total_shares'] = 0

        return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview_analytics(request):
    """
    Advanced analytics endpoint for Overview Dashboard.
    Aggregates data from both Bitaxe and Avalon devices with comprehensive KPIs.
    """
    hours = int(request.query_params.get('hours', 24))
    days = int(request.query_params.get('days', 7))

    start_time_hours = timezone.now() - timedelta(hours=hours)
    start_time_days = timezone.now() - timedelta(days=days)

    # Get all active devices (both types)
    bitaxe_devices = BitAxeDevice.objects.filter(is_active=True)
    avalon_devices = AvalonDevice.objects.filter(is_active=True)
    total_device_count = bitaxe_devices.count() + avalon_devices.count()

    # Mining Statistics Aggregations (both device types)
    bitaxe_mining_recent = BitAxeMiningStats.objects.filter(recorded_at__gte=start_time_hours)
    bitaxe_mining_period = BitAxeMiningStats.objects.filter(recorded_at__gte=start_time_days)
    avalon_mining_recent = AvalonMiningStats.objects.filter(recorded_at__gte=start_time_hours)
    avalon_mining_period = AvalonMiningStats.objects.filter(recorded_at__gte=start_time_days)

    # Hardware Statistics Aggregations (both device types)
    bitaxe_hardware_recent = BitAxeHardwareLog.objects.filter(recorded_at__gte=start_time_hours)
    bitaxe_hardware_period = BitAxeHardwareLog.objects.filter(recorded_at__gte=start_time_days)
    avalon_hardware_recent = AvalonHardwareLogs.objects.filter(recorded_at__gte=start_time_hours)
    avalon_hardware_period = AvalonHardwareLogs.objects.filter(recorded_at__gte=start_time_days)

    # Pool Statistics (Bitaxe only for now)
    pool_stats_recent = BitAxePoolStats.objects.filter(recorded_at__gte=start_time_hours).first()
    pool_stats_period = BitAxePoolStats.objects.filter(recorded_at__gte=start_time_days)

    # Calculate comprehensive KPIs
    result = {
        'overview': {
            'active_devices': total_device_count,
            'bitaxe_devices': bitaxe_devices.count(),
            'avalon_devices': avalon_devices.count(),
            'data_collection_period_hours': hours,
            'analysis_period_days': days,
            'last_updated': timezone.now().isoformat(),
        },
        'mining': {
            'current': {},
            'period': {},
            'efficiency': {},
        },
        'hardware': {
            'current': {},
            'period': {},
            'health': {},
        },
        'pool': {
            'current': {},
            'performance': {},
        },
        'financial': {},
        'trends': {},
    }

    # Current Mining Stats (latest for each device, both types)
    current_hashrate_total_ghs = 0
    current_shares_accepted = 0
    current_shares_rejected = 0

    # Bitaxe devices (report in GH/s)
    for device in bitaxe_devices:
        latest_mining = BitAxeMiningStats.objects.filter(device=device).first()
        if latest_mining:
            current_hashrate_total_ghs += latest_mining.hashrate_ghs or 0
            current_shares_accepted += latest_mining.shares_accepted or 0
            current_shares_rejected += latest_mining.shares_rejected or 0

    # Avalon devices (already report in GH/s)
    for device in avalon_devices:
        latest_mining = AvalonMiningStats.objects.filter(device=device).first()
        if latest_mining:
            # Avalon already reports in GH/s, no conversion needed
            current_hashrate_total_ghs += latest_mining.hashrate_ghs or 0
            current_shares_accepted += latest_mining.shares_accepted or 0
            current_shares_rejected += latest_mining.shares_rejected or 0

    # Get the latest best share from recent data
    current_best_share = BitAxeMiningStats.objects.filter(
        recorded_at__gte=start_time_hours,
        best_difficulty__isnull=False
    ).order_by('-best_difficulty').first()

    result['mining']['current'] = {
        'total_hashrate_ghs': round(current_hashrate_total_ghs, 2),
        'total_hashrate_ths': round(current_hashrate_total_ghs / 1000, 4),
        'total_shares_accepted': current_shares_accepted,
        'total_shares_rejected': current_shares_rejected,
        'rejection_rate': round((current_shares_rejected / (current_shares_accepted + current_shares_rejected) * 100), 2) if (current_shares_accepted + current_shares_rejected) > 0 else 0,
        'acceptance_rate': round((current_shares_accepted / (current_shares_accepted + current_shares_rejected) * 100), 2) if (current_shares_accepted + current_shares_rejected) > 0 else 0,
        'best_share_difficulty': current_best_share.best_difficulty if current_best_share else None,
        'best_share_timestamp': current_best_share.recorded_at.isoformat() if current_best_share else None,
    }

    # Period Mining Stats (aggregated over time for both device types)
    # Bitaxe aggregation
    bitaxe_mining_agg = bitaxe_mining_period.aggregate(
        avg_hashrate=Avg('hashrate_ghs'),
        max_hashrate=Max('hashrate_ghs'),
        min_hashrate=Min('hashrate_ghs'),
        total_shares_period=Sum('shares_accepted'),
        total_rejected_period=Sum('shares_rejected'),
        data_points=Count('id'),
    )

    # Avalon aggregation (also in GH/s)
    avalon_mining_agg = avalon_mining_period.aggregate(
        avg_hashrate=Avg('hashrate_ghs'),
        max_hashrate=Max('hashrate_ghs'),
        min_hashrate=Min('hashrate_ghs'),
        total_shares_period=Sum('shares_accepted'),
        total_rejected_period=Sum('shares_rejected'),
        data_points=Count('id'),
    )

    # Combine both device types
    combined_avg_hashrate = (bitaxe_mining_agg['avg_hashrate'] or 0) + (avalon_mining_agg['avg_hashrate'] or 0)
    combined_max_hashrate = (bitaxe_mining_agg['max_hashrate'] or 0) + (avalon_mining_agg['max_hashrate'] or 0)
    combined_min_hashrate = (bitaxe_mining_agg['min_hashrate'] or 0) + (avalon_mining_agg['min_hashrate'] or 0)
    combined_shares_accepted = (bitaxe_mining_agg['total_shares_period'] or 0) + (avalon_mining_agg['total_shares_period'] or 0)
    combined_shares_rejected = (bitaxe_mining_agg['total_rejected_period'] or 0) + (avalon_mining_agg['total_rejected_period'] or 0)
    combined_data_points = (bitaxe_mining_agg['data_points'] or 0) + (avalon_mining_agg['data_points'] or 0)

    # Get best share from the period
    period_best_share = BitAxeMiningStats.objects.filter(
        recorded_at__gte=start_time_days,
        best_difficulty__isnull=False
    ).order_by('-best_difficulty').first()

    result['mining']['period'] = {
        'avg_hashrate_ghs': round(combined_avg_hashrate, 2),
        'max_hashrate_ghs': round(combined_max_hashrate, 2),
        'min_hashrate_ghs': round(combined_min_hashrate, 2),
        'hashrate_stability': round((combined_min_hashrate / combined_max_hashrate * 100), 1) if combined_max_hashrate else 0,
        'total_shares_accepted': combined_shares_accepted,
        'total_shares_rejected': combined_shares_rejected,
        'total_shares': combined_shares_accepted + combined_shares_rejected,
        'data_points': combined_data_points,
        'best_share_difficulty': period_best_share.best_difficulty if period_best_share else None,
        'best_share_timestamp': period_best_share.recorded_at.isoformat() if period_best_share else None,
    }

    # Mining Efficiency Metrics
    best_share_latest = BitAxeMiningStats.objects.filter(best_difficulty__isnull=False).order_by('-best_difficulty').first()
    result['mining']['efficiency'] = {
        'shares_per_hour': round(combined_shares_accepted / hours, 1) if hours > 0 else 0,
        'shares_per_day': round(combined_shares_accepted / days, 1) if days > 0 else 0,
        'rejection_rate': round((combined_shares_rejected / (combined_shares_accepted + combined_shares_rejected) * 100), 2) if (combined_shares_accepted + combined_shares_rejected) > 0 else 0,
        'best_share_ever': best_share_latest.best_difficulty if best_share_latest else 0,
        'best_share_timestamp': best_share_latest.recorded_at.isoformat() if best_share_latest else None,
        'avg_efficiency': round(combined_avg_hashrate / total_device_count, 2) if total_device_count > 0 else 0,
    }

    # Current Hardware Stats (both device types)
    current_temp_total = 0
    current_power_total = 0
    current_fan_speed_total = 0
    current_temp_count = 0
    current_power_count = 0
    current_fan_speed_count = 0

    # Bitaxe hardware stats
    for device in bitaxe_devices:
        latest_hardware = BitAxeHardwareLog.objects.filter(device=device).first()
        if latest_hardware:
            if latest_hardware.temperature_c:
                current_temp_total += latest_hardware.temperature_c
                current_temp_count += 1
            if latest_hardware.power_watts:
                current_power_total += latest_hardware.power_watts
                current_power_count += 1
            if latest_hardware.fan_speed_rpm:
                current_fan_speed_total += latest_hardware.fan_speed_rpm
                current_fan_speed_count += 1

    # Avalon hardware stats
    for device in avalon_devices:
        latest_hardware = AvalonHardwareLogs.objects.filter(device=device).first()
        if latest_hardware:
            if latest_hardware.temperature_c:
                current_temp_total += latest_hardware.temperature_c
                current_temp_count += 1
            if latest_hardware.power_watts:
                current_power_total += latest_hardware.power_watts
                current_power_count += 1
            if latest_hardware.fan_speed_rpm:
                current_fan_speed_total += latest_hardware.fan_speed_rpm
                current_fan_speed_count += 1

    result['hardware']['current'] = {
        'avg_temperature_c': round(current_temp_total / current_temp_count, 1) if current_temp_count > 0 else 0,
        'total_power_watts': round(current_power_total, 1),
        'avg_fan_speed_rpm': round(current_fan_speed_total / current_fan_speed_count, 0) if current_fan_speed_count > 0 else None,
        'active_devices': current_power_count,
    }

    # Period Hardware Stats (both device types) - using existing queries

    # Bitaxe hardware aggregation
    bitaxe_hardware_agg = bitaxe_hardware_period.aggregate(
        avg_temp=Avg('temperature_c'),
        max_temp=Max('temperature_c'),
        min_temp=Min('temperature_c'),
        avg_power=Avg('power_watts'),
        max_power=Max('power_watts'),
        avg_fan_speed=Avg('fan_speed_rpm'),
        max_fan_speed=Max('fan_speed_rpm'),
        data_points=Count('id'),
    )

    # Avalon hardware aggregation
    avalon_hardware_agg = avalon_hardware_period.aggregate(
        avg_temp=Avg('temperature_c'),
        max_temp=Max('temperature_c'),
        min_temp=Min('temperature_c'),
        avg_power=Avg('power_watts'),
        max_power=Max('power_watts'),
        avg_fan_speed=Avg('fan_speed_rpm'),
        max_fan_speed=Max('fan_speed_rpm'),
        data_points=Count('id'),
    )

    # Combine hardware stats (weighted average where applicable)
    total_hw_data_points = (bitaxe_hardware_agg['data_points'] or 0) + (avalon_hardware_agg['data_points'] or 0)

    if total_hw_data_points > 0:
        combined_avg_temp = (
            (bitaxe_hardware_agg['avg_temp'] or 0) * (bitaxe_hardware_agg['data_points'] or 0) +
            (avalon_hardware_agg['avg_temp'] or 0) * (avalon_hardware_agg['data_points'] or 0)
        ) / total_hw_data_points

        combined_avg_power = (
            (bitaxe_hardware_agg['avg_power'] or 0) * (bitaxe_hardware_agg['data_points'] or 0) +
            (avalon_hardware_agg['avg_power'] or 0) * (avalon_hardware_agg['data_points'] or 0)
        ) / total_hw_data_points

        combined_avg_fan = (
            (bitaxe_hardware_agg['avg_fan_speed'] or 0) * (bitaxe_hardware_agg['data_points'] or 0) +
            (avalon_hardware_agg['avg_fan_speed'] or 0) * (avalon_hardware_agg['data_points'] or 0)
        ) / total_hw_data_points
    else:
        combined_avg_temp = 0
        combined_avg_power = 0
        combined_avg_fan = 0

    combined_max_temp = max(bitaxe_hardware_agg['max_temp'] or 0, avalon_hardware_agg['max_temp'] or 0)
    combined_min_temp = min(bitaxe_hardware_agg['min_temp'] or 999, avalon_hardware_agg['min_temp'] or 999)
    combined_max_power = max(bitaxe_hardware_agg['max_power'] or 0, avalon_hardware_agg['max_power'] or 0)
    combined_max_fan = max(bitaxe_hardware_agg['max_fan_speed'] or 0, avalon_hardware_agg['max_fan_speed'] or 0)

    result['hardware']['period'] = {
        'avg_temperature_c': round(combined_avg_temp, 1),
        'max_temperature_c': round(combined_max_temp, 1),
        'min_temperature_c': round(combined_min_temp if combined_min_temp < 999 else 0, 1),
        'avg_power_watts': round(combined_avg_power, 1),
        'max_power_watts': round(combined_max_power, 1),
        'avg_fan_speed_rpm': round(combined_avg_fan, 0),
        'max_fan_speed_rpm': round(combined_max_fan, 0),
        'data_points': total_hw_data_points,
    }

    # Hardware Health Metrics
    temp_range = combined_max_temp - (combined_min_temp if combined_min_temp < 999 else 0) if combined_max_temp else 0
    result['hardware']['health'] = {
        'temperature_range_c': round(temp_range, 1),
        'temperature_stability': 100 - min(temp_range * 2, 100),  # Lower range = better stability
        'thermal_efficiency': round(combined_avg_hashrate / combined_avg_temp, 2) if combined_avg_temp > 0 else 0,
        'power_efficiency_gh_per_watt': round(combined_avg_hashrate / combined_avg_power, 2) if combined_avg_power > 0 else 0,
    }

    # Pool Statistics
    if pool_stats_recent:
        result['pool']['current'] = {
            'hashrate_1m': pool_stats_recent.hashrate_1m,
            'hashrate_5m': pool_stats_recent.hashrate_5m,
            'hashrate_1hr': pool_stats_recent.hashrate_1hr,
            'hashrate_1d': pool_stats_recent.hashrate_1d,
            'hashrate_ghs': round(pool_stats_recent.hashrate_1m_ghs or 0, 2),
            'pool_hashrate_ghs': round(pool_stats_recent.hashrate_1m_ghs or 0, 2),  # Alias for frontend compatibility
            'total_shares': pool_stats_recent.shares or 0,
            'best_share': pool_stats_recent.bestshare or 0,
            'workers': pool_stats_recent.workers or 0,
            'workers_active': pool_stats_recent.workers or 0,  # Alias for frontend compatibility
            'network_difficulty': 95000000000000,  # Current estimated network difficulty (95T)
        }

    pool_agg = pool_stats_period.aggregate(
        avg_hashrate=Avg('hashrate_1m_ghs'),
        max_hashrate=Max('hashrate_1m_ghs'),
        avg_workers=Avg('workers'),
        max_best_share=Max('bestshare'),
    )

    # Calculate stale share rate as approximation from overall rejection rate
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

    # Financial Calculations (estimates)
    btc_block_reward = 3.125  # Current block reward after halving
    network_hashrate_ehs = 650  # Estimated network hashrate in EH/s (650,000 PH/s)
    btc_price_usd = 67000  # Approximate BTC price (should be fetched from API in production)

    # Calculate expected BTC per day
    network_hashrate_ghs = network_hashrate_ehs * 1e9  # Convert to GH/s
    pool_percentage = (current_hashrate_total_ghs / network_hashrate_ghs) * 100 if network_hashrate_ghs > 0 else 0
    blocks_per_day = 144  # ~144 blocks per day (10 min per block)
    expected_btc_per_day = (current_hashrate_total_ghs / network_hashrate_ghs) * blocks_per_day * btc_block_reward

    # Energy costs
    kwh_price = 0.12  # USD per kWh (average)
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
        'roi_years': round(1500 / (((expected_btc_per_day * btc_price_usd) - energy_cost_per_day) * 365), 2) if (expected_btc_per_day * btc_price_usd) > energy_cost_per_day and ((expected_btc_per_day * btc_price_usd) - energy_cost_per_day) > 0 else None,
        'assumptions': {
            'btc_price_usd': btc_price_usd,
            'network_hashrate_ehs': network_hashrate_ehs,
            'kwh_price_usd': kwh_price,
            'device_cost_usd': 1500,
        }
    }

    # Performance Trends (hourly averages for last 24h)
    from django.db.models.functions import TruncHour

    # Combine Bitaxe and Avalon mining trends
    bitaxe_hourly_mining = bitaxe_mining_recent.annotate(
        hour=TruncHour('recorded_at')
    ).values('hour').annotate(
        avg_hashrate=Avg('hashrate_ghs'),
        total_shares=Sum('shares_accepted'),
    ).order_by('hour')

    avalon_hourly_mining = avalon_mining_recent.annotate(
        hour=TruncHour('recorded_at')
    ).values('hour').annotate(
        avg_hashrate=Avg('hashrate_ghs'),
        total_shares=Sum('shares_accepted'),
    ).order_by('hour')

    # Combine Bitaxe and Avalon hardware trends
    bitaxe_hourly_hardware = bitaxe_hardware_recent.annotate(
        hour=TruncHour('recorded_at')
    ).values('hour').annotate(
        avg_temp=Avg('temperature_c'),
        avg_power=Avg('power_watts'),
    ).order_by('hour')

    avalon_hourly_hardware = avalon_hardware_recent.annotate(
        hour=TruncHour('recorded_at')
    ).values('hour').annotate(
        avg_temp=Avg('temperature_c'),
        avg_power=Avg('power_watts'),
    ).order_by('hour')

    # Combine hourly data for trends
    combined_hourly_mining = {}
    combined_hourly_hardware = {}

    # Aggregate Bitaxe hourly mining data
    for item in bitaxe_hourly_mining:
        hour_key = item['hour'].isoformat()
        combined_hourly_mining[hour_key] = {
            'hour': hour_key,
            'hashrate_ghs': item['avg_hashrate'] or 0,
            'shares': item['total_shares'] or 0,
        }

    # Add Avalon hourly mining data
    for item in avalon_hourly_mining:
        hour_key = item['hour'].isoformat()
        if hour_key in combined_hourly_mining:
            combined_hourly_mining[hour_key]['hashrate_ghs'] += item['avg_hashrate'] or 0
            combined_hourly_mining[hour_key]['shares'] += item['total_shares'] or 0
        else:
            combined_hourly_mining[hour_key] = {
                'hour': hour_key,
                'hashrate_ghs': item['avg_hashrate'] or 0,
                'shares': item['total_shares'] or 0,
            }

    # Aggregate Bitaxe hourly hardware data
    for item in bitaxe_hourly_hardware:
        hour_key = item['hour'].isoformat()
        combined_hourly_hardware[hour_key] = {
            'hour': hour_key,
            'temperature_c': item['avg_temp'] or 0,
            'power_watts': item['avg_power'] or 0,
            'device_count': 1,
        }

    # Add Avalon hourly hardware data (weighted average for temperature)
    for item in avalon_hourly_hardware:
        hour_key = item['hour'].isoformat()
        if hour_key in combined_hourly_hardware:
            # Weighted average for temperature, sum for power
            old_temp = combined_hourly_hardware[hour_key]['temperature_c']
            old_count = combined_hourly_hardware[hour_key]['device_count']
            new_temp = (old_temp * old_count + (item['avg_temp'] or 0)) / (old_count + 1)
            combined_hourly_hardware[hour_key]['temperature_c'] = new_temp
            combined_hourly_hardware[hour_key]['power_watts'] += item['avg_power'] or 0
            combined_hourly_hardware[hour_key]['device_count'] += 1
        else:
            combined_hourly_hardware[hour_key] = {
                'hour': hour_key,
                'temperature_c': item['avg_temp'] or 0,
                'power_watts': item['avg_power'] or 0,
                'device_count': 1,
            }

    # Best Share Trends (hourly maximums for last 24h)
    bitaxe_hourly_best_shares = bitaxe_mining_recent.filter(
        best_difficulty__isnull=False
    ).annotate(
        hour=TruncHour('recorded_at')
    ).values('hour').annotate(
        best_share_difficulty=Max('best_difficulty'),
        device_name=Max('device__device_name'),
    ).order_by('hour')

    # For Avalon, we'll use the general difficulty field as best share if available
    # The difficulty field actually stores the best share value from the Avalon API
    avalon_hourly_best_shares = avalon_mining_recent.filter(
        difficulty__gt=1000  # Only consider meaningful best shares (> 1K difficulty)
    ).annotate(
        hour=TruncHour('recorded_at')
    ).values('hour').annotate(
        best_share_difficulty=Max('difficulty'),
        device_name=Max('device__device_name'),
    ).order_by('hour')

    # Combine best share data - merge both devices into single hourly entries
    combined_hourly_best_shares = {}

    # Initialize all hours from combined mining data
    for hour_key in combined_hourly_mining.keys():
        combined_hourly_best_shares[hour_key] = {
            'hour': hour_key,
            'bitaxe_best_share': 0,
            'bitaxe_device_name': None,
            'avalon_best_share': 0,
            'avalon_device_name': None,
            'hashrate_ghs': combined_hourly_mining[hour_key].get('hashrate_ghs', 0),
        }

    # Add Bitaxe best shares
    for item in bitaxe_hourly_best_shares:
        hour_key = item['hour'].isoformat()
        if hour_key in combined_hourly_best_shares:
            combined_hourly_best_shares[hour_key]['bitaxe_best_share'] = item['best_share_difficulty'] or 0
            combined_hourly_best_shares[hour_key]['bitaxe_device_name'] = item['device_name'] or 'Unknown'
        else:
            combined_hourly_best_shares[hour_key] = {
                'hour': hour_key,
                'bitaxe_best_share': item['best_share_difficulty'] or 0,
                'bitaxe_device_name': item['device_name'] or 'Unknown',
                'avalon_best_share': 0,
                'avalon_device_name': None,
                'hashrate_ghs': combined_hourly_mining.get(hour_key, {}).get('hashrate_ghs', 0),
            }

    # Add Avalon best shares
    for item in avalon_hourly_best_shares:
        hour_key = item['hour'].isoformat()
        if hour_key in combined_hourly_best_shares:
            combined_hourly_best_shares[hour_key]['avalon_best_share'] = item['best_share_difficulty'] or 0
            combined_hourly_best_shares[hour_key]['avalon_device_name'] = item['device_name'] or 'Unknown'
        else:
            combined_hourly_best_shares[hour_key] = {
                'hour': hour_key,
                'bitaxe_best_share': 0,
                'bitaxe_device_name': None,
                'avalon_best_share': item['best_share_difficulty'] or 0,
                'avalon_device_name': item['device_name'] or 'Unknown',
                'hashrate_ghs': combined_hourly_mining.get(hour_key, {}).get('hashrate_ghs', 0),
            }

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


# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and create session.
    Expects: {"username": "...", "password": "..."}
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        })
    else:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
def logout_view(request):
    """Logout user and destroy session."""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([AllowAny])
def current_user_view(request):
    """Get current authenticated user info."""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            }
        })
    else:
        return Response({'authenticated': False})


@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token_view(request):
    """
    Return CSRF token for the client.
    This endpoint ensures the CSRF cookie is set.
    """
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    return Response({'csrfToken': csrf_token})


# Data Collector Settings Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def collector_settings_view(request):
    """
    GET: Get current data collector settings from database.
    POST: Update data collector settings in database.
    The data collector service fetches settings from the database independently.
    """
    if request.method == 'GET':
        try:
            # Get settings from database
            settings = CollectorSettings.get_settings()
            settings_data = CollectorSettingsSerializer(settings).data
            return Response(settings_data)

        except Exception as e:
            logger.error(f"Error getting collector settings: {e}")
            return Response({
                'error': str(e),
                'polling_interval_minutes': 15,
                'device_check_interval_minutes': 5,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        try:
            # Get or create settings instance
            settings = CollectorSettings.get_settings()

            # Update with provided data
            serializer = CollectorSettingsSerializer(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Collector settings updated: {serializer.data}")

                return Response({
                    'success': True,
                    'message': 'Settings saved successfully. Changes will take effect on the next polling cycle.',
                    'settings': serializer.data,
                })
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors,
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error saving collector settings: {e}")
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_network_data(request):
    """
    Fetch and cache latest Bitcoin price and network hashrate from public APIs.
    """
    import requests
    from django.utils import timezone as tz

    try:
        settings = CollectorSettings.get_settings()

        btc_price = None
        network_hashrate = None
        network_difficulty = None
        errors = []

        # Fetch BTC price from CoinGecko (free, no API key required)
        try:
            price_response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
                timeout=10
            )
            if price_response.ok:
                price_data = price_response.json()
                btc_price = price_data.get('bitcoin', {}).get('usd')
                if btc_price:
                    settings.cached_btc_price = btc_price
                    logger.info(f"Updated BTC price: ${btc_price}")
        except Exception as e:
            errors.append(f"Failed to fetch BTC price: {str(e)}")
            logger.warning(f"Failed to fetch BTC price: {e}")

        # Fetch network stats from mempool.space (free, no API key required)
        try:
            hashrate_response = requests.get(
                'https://mempool.space/api/v1/mining/hashrate/3d',
                timeout=10
            )
            if hashrate_response.ok:
                hashrate_data = hashrate_response.json()
                # Get latest hashrate (in H/s), convert to EH/s
                if hashrate_data.get('currentHashrate'):
                    network_hashrate = hashrate_data['currentHashrate'] / 1e18  # Convert to EH/s
                    settings.cached_network_hashrate = network_hashrate
                    logger.info(f"Updated network hashrate: {network_hashrate:.2f} EH/s")
                if hashrate_data.get('currentDifficulty'):
                    network_difficulty = hashrate_data['currentDifficulty']
                    settings.cached_network_difficulty = network_difficulty
                    logger.info(f"Updated network difficulty: {network_difficulty}")
        except Exception as e:
            errors.append(f"Failed to fetch network hashrate: {str(e)}")
            logger.warning(f"Failed to fetch network hashrate: {e}")

        # Update timestamp
        settings.network_data_updated_at = tz.now()
        settings.save()

        return Response({
            'success': True,
            'message': 'Network data refreshed',
            'data': {
                'btc_price': float(settings.cached_btc_price),
                'network_hashrate_ehs': float(settings.cached_network_hashrate),
                'network_difficulty': float(settings.cached_network_difficulty),
                'updated_at': settings.network_data_updated_at.isoformat() if settings.network_data_updated_at else None,
            },
            'errors': errors if errors else None,
        })

    except Exception as e:
        logger.error(f"Error refreshing network data: {e}")
        return Response({
            'success': False,
            'error': str(e),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_network_data(request):
    """
    Get cached network data (BTC price, hashrate, difficulty).
    """
    try:
        settings = CollectorSettings.get_settings()

        return Response({
            'btc_price': float(settings.cached_btc_price),
            'network_hashrate_ehs': float(settings.cached_network_hashrate),
            'network_difficulty': float(settings.cached_network_difficulty),
            'updated_at': settings.network_data_updated_at.isoformat() if settings.network_data_updated_at else None,
        })

    except Exception as e:
        logger.error(f"Error getting network data: {e}")
        return Response({
            'error': str(e),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_collector_poll(request):
    """
    Trigger a manual data collection poll.
    """
    import os

    import requests

    data_service_url = os.environ.get('DATA_SERVICE_URL', 'http://data-service:5000')

    try:
        response = requests.post(f'{data_service_url}/poll', timeout=60)
        if response.ok:
            return Response({
                'success': True,
                'message': 'Poll cycle triggered successfully',
                'result': response.json()
            })
        return Response(
            {'error': 'Failed to trigger poll'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering poll: {e}")
        return Response(
            {'error': 'Data collector service unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detailed_analytics(request):
    """
    Advanced analytics endpoint for the Analytics Dashboard.
    Includes:
    - Energy cost analysis and efficiency metrics
    - Best difficulty prediction based on hashrate and probability
    - Historical best difficulty analysis
    - Cross-device comparisons
    - Predictive insights
    """
    import math

    from django.db.models.functions import TruncDay, TruncHour

    hours = int(request.query_params.get('hours', 24))
    days = int(request.query_params.get('days', 7))

    start_time_hours = timezone.now() - timedelta(hours=hours)
    start_time_days = timezone.now() - timedelta(days=days)

    # Get all active devices
    bitaxe_devices = BitAxeDevice.objects.filter(is_active=True)
    avalon_devices = AvalonDevice.objects.filter(is_active=True)

    result = {
        'energy_analysis': {},
        'best_difficulty_prediction': {},
        'historical_best_shares': {},
        'device_comparison': {},
        'cost_analysis': {},
        'efficiency_trends': [],
        'predictions': {},
    }

    # === ENERGY ANALYSIS ===
    # Get current and historical power consumption
    current_power_total = 0
    device_power_data = []

    for device in bitaxe_devices:
        latest_hw = BitAxeHardwareLog.objects.filter(device=device).first()
        latest_mining = BitAxeMiningStats.objects.filter(device=device).first()
        if latest_hw:
            power = latest_hw.power_watts or 0
            hashrate = latest_mining.hashrate_ghs if latest_mining else 0
            current_power_total += power
            device_power_data.append({
                'device_name': device.device_name,
                'device_type': 'Bitaxe',
                'power_watts': round(power, 1),
                'hashrate_ghs': round(hashrate, 2),
                'efficiency_w_per_gh': round(power / hashrate, 2) if hashrate > 0 else 0,
                'efficiency_j_per_th': round((power / hashrate) * 1000, 2) if hashrate > 0 else 0,
            })

    for device in avalon_devices:
        latest_hw = AvalonHardwareLogs.objects.filter(device=device).first()
        latest_mining = AvalonMiningStats.objects.filter(device=device).first()
        if latest_hw:
            power = latest_hw.power_watts or 0
            hashrate = latest_mining.hashrate_ghs if latest_mining else 0
            current_power_total += power
            device_power_data.append({
                'device_name': device.device_name,
                'device_type': 'Avalon',
                'power_watts': round(power, 1),
                'hashrate_ghs': round(hashrate, 2),
                'efficiency_w_per_gh': round(power / hashrate, 2) if hashrate > 0 else 0,
                'efficiency_j_per_th': round((power / hashrate) * 1000, 2) if hashrate > 0 else 0,
            })

    # Historical power data (hourly averages)
    bitaxe_power_trend = BitAxeHardwareLog.objects.filter(
        recorded_at__gte=start_time_hours
    ).annotate(hour=TruncHour('recorded_at')).values('hour').annotate(
        avg_power=Avg('power_watts'),
        avg_temp=Avg('temperature_c'),
    ).order_by('hour')

    avalon_power_trend = AvalonHardwareLogs.objects.filter(
        recorded_at__gte=start_time_hours
    ).annotate(hour=TruncHour('recorded_at')).values('hour').annotate(
        avg_power=Avg('power_watts'),
        avg_temp=Avg('temperature_c'),
    ).order_by('hour')

    # Combine power trends
    power_by_hour = {}
    for item in bitaxe_power_trend:
        hour_key = item['hour'].isoformat()
        power_by_hour[hour_key] = {
            'hour': hour_key,
            'power_watts': item['avg_power'] or 0,
            'temperature_c': item['avg_temp'] or 0,
        }
    for item in avalon_power_trend:
        hour_key = item['hour'].isoformat()
        if hour_key in power_by_hour:
            power_by_hour[hour_key]['power_watts'] += item['avg_power'] or 0
            power_by_hour[hour_key]['temperature_c'] = (
                power_by_hour[hour_key]['temperature_c'] + (item['avg_temp'] or 0)
            ) / 2
        else:
            power_by_hour[hour_key] = {
                'hour': hour_key,
                'power_watts': item['avg_power'] or 0,
                'temperature_c': item['avg_temp'] or 0,
            }

    result['energy_analysis'] = {
        'current_power_watts': round(current_power_total, 1),
        'current_power_kw': round(current_power_total / 1000, 3),
        'devices': sorted(device_power_data, key=lambda x: x['power_watts'], reverse=True),
        'power_trend': sorted(power_by_hour.values(), key=lambda x: x['hour']),
    }

    # === BEST DIFFICULTY PREDICTION ===
    # Get current hashrate (total across all devices)
    total_hashrate_ghs = sum(d['hashrate_ghs'] for d in device_power_data)
    total_hashrate_hs = total_hashrate_ghs * 1e9  # Convert GH/s to H/s

    # Get historical best difficulties to analyze patterns
    bitaxe_best_shares = BitAxeMiningStats.objects.filter(
        best_difficulty__isnull=False,
        best_difficulty__gt=0
    ).order_by('-best_difficulty')[:100]

    avalon_best_shares = AvalonMiningStats.objects.filter(
        difficulty__gt=1000
    ).order_by('-difficulty')[:100]

    # All-time best share - check BOTH Bitaxe and Avalon devices
    bitaxe_best = bitaxe_best_shares.first()
    avalon_best = avalon_best_shares.first()

    bitaxe_best_diff = int(bitaxe_best.best_difficulty) if bitaxe_best and bitaxe_best.best_difficulty else 0
    avalon_best_diff = int(avalon_best.difficulty) if avalon_best and avalon_best.difficulty else 0

    # Use the higher of the two
    if bitaxe_best_diff >= avalon_best_diff:
        all_time_best = bitaxe_best
        all_time_best_difficulty = bitaxe_best_diff
        all_time_best_source = 'Bitaxe'
    else:
        all_time_best = avalon_best
        all_time_best_difficulty = avalon_best_diff
        all_time_best_source = 'Avalon'

    # Debug logging
    logger.info(f"Analytics: total_hashrate_ghs={total_hashrate_ghs}, all_time_best_difficulty={all_time_best_difficulty}, source={all_time_best_source}")

    # Calculate probability of finding a share above current best
    #
    # IMPORTANT: Share difficulty is NOT the same as the number of hashes needed.
    # In Bitcoin mining, share difficulty D means you need on average 2^32 * D hashes
    # to find a share that meets that difficulty.
    #
    # Probability of a single hash meeting difficulty D = 1 / (2^32 * D)
    # Expected hashes to beat difficulty D = 2^32 * D
    # Expected time to beat D = (2^32 * D) / hashrate_hs

    if total_hashrate_hs > 0 and all_time_best_difficulty > 0:
        # Bitcoin share difficulty calculation:
        #
        # In Bitcoin, difficulty D means you need to find a hash below target = 2^256 / (D * 2^32)
        # The probability of a single hash meeting difficulty D is: 1 / (D * 2^32)
        #
        # Expected number of hashes to find a share with difficulty >= D: D * 2^32
        # Expected time: (D * 2^32) / hashrate_hs seconds
        #
        # 2^32 = 4,294,967,296 ≈ 4.295 billion

        TWO_POW_32 = 4294967296  # 2^32

        # Expected time to find a share equal to or better than current best
        expected_seconds = (all_time_best_difficulty * TWO_POW_32) / total_hashrate_hs
        expected_hours = expected_seconds / 3600
        expected_days = expected_hours / 24

        # Probability of beating current best within a time period
        # Using exponential distribution: P(T <= t) = 1 - exp(-t/E[T])
        # E[T] = (D * 2^32) / hashrate
        # P = 1 - exp(-t * hashrate / (D * 2^32))

        # Calculate lambda = hashrate / (difficulty * 2^32) (rate parameter)
        lambda_rate = total_hashrate_hs / (all_time_best_difficulty * TWO_POW_32)

        # Probability of beating current best within next hour
        prob_beat_1h = 1 - math.exp(-3600 * lambda_rate)
        # Probability within next 24 hours
        prob_beat_24h = 1 - math.exp(-86400 * lambda_rate)
        # Probability within next 7 days
        prob_beat_7d = 1 - math.exp(-604800 * lambda_rate)

        # Clamp probabilities to avoid floating point issues showing > 100%
        prob_beat_1h = min(max(prob_beat_1h, 0), 1)
        prob_beat_24h = min(max(prob_beat_24h, 0), 1)
        prob_beat_7d = min(max(prob_beat_7d, 0), 1)

        # Log the calculated values for debugging
        logger.info(f"Analytics: expected_hours={expected_hours:.2f}, prob_1h={prob_beat_1h*100:.4f}%, prob_24h={prob_beat_24h*100:.4f}%, prob_7d={prob_beat_7d*100:.4f}%")

        # The "Expected Best" values are removed - they were confusing.
        # Instead, we focus on the key question: "When will I beat my current best?"
        #
        # This is answered by:
        # - expected_time_to_beat (already calculated above)
        # - probability_to_beat_current_best (already calculated above)
        #
        # Setting these to 0 as they're not meaningful to display
        expected_best_in_1d = 0
        expected_best_in_7d = 0
        expected_best_in_30d = 0
    else:
        expected_hours = 0
        expected_days = 0
        prob_beat_1h = 0
        prob_beat_24h = 0
        prob_beat_7d = 0
        expected_best_in_1d = 0
        expected_best_in_7d = 0
        expected_best_in_30d = 0

    # Recent best shares timeline (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_bitaxe_bests = BitAxeMiningStats.objects.filter(
        recorded_at__gte=thirty_days_ago,
    ).filter(
        Q(best_difficulty__isnull=False, best_difficulty__gt=0) |
        Q(best_session_difficulty__isnull=False, best_session_difficulty__gt=0)
    ).annotate(day=TruncDay('recorded_at')).values('day').annotate(
        max_best_ever=Max('best_difficulty'),           # All-time best
        max_best_session=Max('best_session_difficulty'), # Session best
        device_name=Max('device__device_name'),
    ).order_by('day')

    recent_avalon_bests = AvalonMiningStats.objects.filter(
        recorded_at__gte=thirty_days_ago,
        difficulty__gt=1000
    ).annotate(day=TruncDay('recorded_at')).values('day').annotate(
        max_difficulty=Max('difficulty'),
        device_name=Max('device__device_name'),
    ).order_by('day')

    # Combine daily best shares
    daily_bests = {}
    for item in recent_bitaxe_bests:
        day_key = item['day'].isoformat()
        daily_bests[day_key] = {
            'date': day_key,
            'best_difficulty': item['max_best_ever'] or 0,
            'best_session_difficulty': item['max_best_session'] or 0,
            'device_name': item['device_name'],
            'device_type': 'Bitaxe',
        }
    for item in recent_avalon_bests:
        day_key = item['day'].isoformat()
        # Avalon doesn't have session tracking, so use difficulty for both
        if day_key not in daily_bests or item['max_difficulty'] > daily_bests[day_key]['best_difficulty']:
            daily_bests[day_key] = {
                'date': day_key,
                'best_difficulty': item['max_difficulty'],
                'best_session_difficulty': item['max_difficulty'],  # Same as best for Avalon
                'device_name': item['device_name'],
                'device_type': 'Avalon',
            }
        elif day_key in daily_bests:
            # Keep existing best_difficulty but update session if Avalon has higher
            if item['max_difficulty'] > daily_bests[day_key].get('best_session_difficulty', 0):
                daily_bests[day_key]['best_session_difficulty'] = item['max_difficulty']

    # Sort daily bests by date
    sorted_daily_bests = sorted(daily_bests.values(), key=lambda x: x['date'])

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
            '1_day': round(expected_best_in_1d),
            '7_days': round(expected_best_in_7d),
            '30_days': round(expected_best_in_30d),
            '1_day_formatted': _format_difficulty(expected_best_in_1d),
            '7_days_formatted': _format_difficulty(expected_best_in_7d),
            '30_days_formatted': _format_difficulty(expected_best_in_30d),
        },
        'daily_best_shares': sorted_daily_bests,
    }

    # === HISTORICAL BEST SHARES ANALYSIS ===
    # Top 10 best shares ever - group by device and difficulty to avoid duplicates
    # Use distinct values and get the first occurrence of each unique best_difficulty per device
    from django.db.models import F, Window
    from django.db.models.functions import RowNumber

    # For Bitaxe: Get unique (device, best_difficulty) combinations with earliest timestamp
    bitaxe_unique_bests = BitAxeMiningStats.objects.filter(
        best_difficulty__isnull=False,
        best_difficulty__gt=0
    ).values('device__device_name', 'best_difficulty').annotate(
        first_timestamp=Min('recorded_at'),
        hashrate=Avg('hashrate_ghs'),
    ).order_by('-best_difficulty')[:20]  # Get more to allow for dedup

    # For Avalon: Get unique (device, difficulty) combinations
    avalon_unique_bests = AvalonMiningStats.objects.filter(
        difficulty__gt=1000
    ).values('device__device_name', 'difficulty').annotate(
        first_timestamp=Min('recorded_at'),
        hashrate=Avg('hashrate_ghs'),
    ).order_by('-difficulty')[:20]

    top_shares = []
    seen_difficulties = set()  # Track seen difficulties to avoid exact duplicates

    for share in bitaxe_unique_bests:
        diff = share['best_difficulty']
        # Create a unique key combining device and difficulty
        key = (share['device__device_name'], diff)
        if key not in seen_difficulties:
            seen_difficulties.add(key)
            top_shares.append({
                'difficulty': diff,
                'difficulty_formatted': _format_difficulty(diff),
                'device_name': share['device__device_name'],
                'device_type': 'Bitaxe',
                'timestamp': share['first_timestamp'].isoformat() if share['first_timestamp'] else None,
                'hashrate_at_time': round(share['hashrate'] or 0, 2),
            })

    for share in avalon_unique_bests:
        diff = share['difficulty']
        key = (share['device__device_name'], diff)
        if key not in seen_difficulties:
            seen_difficulties.add(key)
            top_shares.append({
                'difficulty': diff,
                'difficulty_formatted': _format_difficulty(diff),
                'device_name': share['device__device_name'],
                'device_type': 'Avalon',
                'timestamp': share['first_timestamp'].isoformat() if share['first_timestamp'] else None,
                'hashrate_at_time': round(share['hashrate'] or 0, 2),
            })

    top_shares = sorted(top_shares, key=lambda x: x['difficulty'], reverse=True)[:10]

    result['historical_best_shares'] = {
        'top_10': top_shares,
        'total_records_bitaxe': bitaxe_best_shares.count(),
        'total_records_avalon': avalon_best_shares.count(),
    }

    # === COST ANALYSIS ===
    # Get settings from database
    settings = CollectorSettings.get_settings()

    # Use settings for energy costs and network data
    kwh_price = float(settings.energy_rate)
    energy_currency = settings.energy_currency
    show_revenue = settings.show_revenue_stats
    btc_price = float(settings.cached_btc_price)
    network_hashrate_ehs = float(settings.cached_network_hashrate)
    network_difficulty = float(settings.cached_network_difficulty)
    network_data_updated = settings.network_data_updated_at

    # Daily/monthly energy calculations
    power_kw = current_power_total / 1000
    daily_kwh = power_kw * 24
    monthly_kwh = daily_kwh * 30
    yearly_kwh = daily_kwh * 365

    daily_cost = daily_kwh * kwh_price
    monthly_cost = monthly_kwh * kwh_price
    yearly_cost = yearly_kwh * kwh_price

    # Mining revenue estimation (only if enabled)
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

    # Only include revenue stats if enabled
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

    # === DEVICE COMPARISON ===
    device_stats = []
    for device in bitaxe_devices:
        latest_mining = BitAxeMiningStats.objects.filter(device=device).first()
        latest_hw = BitAxeHardwareLog.objects.filter(device=device).first()

        # Get best difficulty for this device
        device_best = BitAxeMiningStats.objects.filter(
            device=device,
            best_difficulty__isnull=False,
            best_difficulty__gt=0
        ).order_by('-best_difficulty').first()

        if latest_mining and latest_hw:
            device_stats.append({
                'device_name': device.device_name,
                'device_type': 'Bitaxe',
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

    for device in avalon_devices:
        latest_mining = AvalonMiningStats.objects.filter(device=device).first()
        latest_hw = AvalonHardwareLogs.objects.filter(device=device).first()

        device_best = AvalonMiningStats.objects.filter(
            device=device,
            difficulty__gt=1000
        ).order_by('-difficulty').first()

        if latest_mining and latest_hw:
            device_stats.append({
                'device_name': device.device_name,
                'device_type': 'Avalon',
                'hashrate_ghs': round(latest_mining.hashrate_ghs or 0, 2),
                'power_watts': round(latest_hw.power_watts or 0, 1),
                'temperature_c': round(latest_hw.temperature_c or 0, 1),
                'efficiency_j_per_th': round(latest_hw.efficiency_j_per_th or 0, 2),
                'best_difficulty': device_best.difficulty if device_best else 0,
                'best_difficulty_formatted': _format_difficulty(device_best.difficulty) if device_best else '0',
                'uptime_hours': round((latest_mining.uptime_seconds or 0) / 3600, 1),
                'shares_accepted': latest_mining.shares_accepted or 0,
                'shares_rejected': latest_mining.shares_rejected or 0,
            })

    result['device_comparison'] = {
        'devices': sorted(device_stats, key=lambda x: x['hashrate_ghs'], reverse=True),
        'total_devices': len(device_stats),
    }

    # === EFFICIENCY TRENDS (daily) ===
    daily_efficiency = BitAxeHardwareLog.objects.filter(
        recorded_at__gte=start_time_days
    ).annotate(day=TruncDay('recorded_at')).values('day').annotate(
        avg_efficiency=Avg('efficiency_j_per_th'),
        avg_power=Avg('power_watts'),
        avg_temp=Avg('temperature_c'),
    ).order_by('day')

    result['efficiency_trends'] = [
        {
            'date': item['day'].isoformat(),
            'efficiency_j_per_th': round(item['avg_efficiency'] or 0, 2),
            'avg_power_watts': round(item['avg_power'] or 0, 1),
            'avg_temperature_c': round(item['avg_temp'] or 0, 1),
        }
        for item in daily_efficiency
    ]

    # === PREDICTIONS SUMMARY ===
    result['predictions'] = {
        'next_best_share': {
            'estimated_time': _format_time_duration(expected_hours),
            'confidence': 'medium' if prob_beat_24h > 0.5 else 'low' if prob_beat_24h > 0.1 else 'very_low',
            'probability_24h': round(prob_beat_24h * 100, 2),
        },
        'efficiency_trend': 'stable',  # Could be calculated from trends
        'power_consumption_trend': 'stable',  # Could be calculated from trends
    }

    return Response(result)


def _format_difficulty(difficulty):
    """Format difficulty number to human-readable string."""
    if difficulty is None or difficulty == 0:
        return '0'
    if difficulty >= 1e15:
        return f'{difficulty / 1e15:.2f}P'
    if difficulty >= 1e12:
        return f'{difficulty / 1e12:.2f}T'
    if difficulty >= 1e9:
        return f'{difficulty / 1e9:.2f}G'
    if difficulty >= 1e6:
        return f'{difficulty / 1e6:.2f}M'
    if difficulty >= 1e3:
        return f'{difficulty / 1e3:.2f}K'
    return str(int(difficulty))


def _format_time_duration(hours):
    """Format hours to human-readable duration string."""
    if hours < 1:
        return f'{int(hours * 60)} minutes'
    if hours < 24:
        return f'{hours:.1f} hours'
    if hours < 168:  # 7 days
        return f'{hours / 24:.1f} days'
    if hours < 720:  # 30 days
        return f'{hours / 168:.1f} weeks'
    if hours < 8760:  # 365 days
        return f'{hours / 720:.1f} months'
    return f'{hours / 8760:.1f} years'

