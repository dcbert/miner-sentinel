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
    BitAxeDevice,
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)
from .models import AvalonDevice  # legacy mirror
from .serializers import (
    BitAxeDeviceSerializer,
    BitAxeDeviceWriteSerializer,
    CollectorSettingsSerializer,
    DeviceSerializer,
    DeviceWriteSerializer,
)
from .unified_serializers import (
    UnifiedDeviceAsAvalonSerializer,
    UnifiedDeviceAsBitaxeSerializer,
    UnifiedHardwareSerializer,
    UnifiedMiningAsAvalonSerializer,
    UnifiedMiningAsBitaxeSerializer,
    UnifiedPoolAsLegacySerializer,
    UnifiedSystemAsAvalonSerializer,
    UnifiedSystemAsBitaxeSerializer,
)
from .analytics_unified import detailed_analytics, overview_analytics

logger = logging.getLogger(__name__)

_MAX_HOURS = 24 * 90
_MAX_DAYS = 90


def _parse_int_param(value, default, min_value=1, max_value=None):
    """Safely parse a positive integer query param with optional bounds."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < min_value:
        n = min_value
    if max_value is not None and n > max_value:
        n = max_value
    return n


def _mirror_unified_to_legacy(device: Device) -> None:
    """Keep legacy registry rows in sync for dual-path collectors/admin."""
    if device.make == Device.MAKE_BITAXE:
        BitAxeDevice.objects.update_or_create(
            device_id=device.device_id,
            defaults={
                'device_name': device.name,
                'ip_address': device.ip_address,
                'is_active': device.is_active,
                'last_seen_at': device.last_seen_at,
                'error_message': device.error_message,
            },
        )
    elif device.make == Device.MAKE_AVALON:
        AvalonDevice.objects.update_or_create(
            device_id=device.device_id,
            defaults={
                'device_name': device.name,
                'ip_address': device.ip_address,
                'is_active': device.is_active,
                'last_seen_at': device.last_seen_at,
                'error_message': device.error_message,
            },
        )


def _delete_legacy_mirror(make: str, device_id: str) -> None:
    if make == Device.MAKE_BITAXE:
        BitAxeDevice.objects.filter(device_id=device_id).delete()
    elif make == Device.MAKE_AVALON:
        AvalonDevice.objects.filter(device_id=device_id).delete()


class DeviceViewSet(viewsets.ModelViewSet):
    """
    Unified device registry CRUD.
    Mirrors Bitaxe/Avalon rows into legacy tables for compatibility.
    """
    queryset = Device.objects.all().order_by('make', 'name')
    serializer_class = DeviceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        make = self.request.query_params.get('make')
        if make:
            qs = qs.filter(make=make)
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            qs = qs.filter(is_active=True)
        return qs

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DeviceWriteSerializer
        return DeviceSerializer

    def perform_create(self, serializer):
        device = serializer.save()
        _mirror_unified_to_legacy(device)

    def perform_update(self, serializer):
        device = serializer.save()
        _mirror_unified_to_legacy(device)

    def perform_destroy(self, instance):
        make, device_id = instance.make, instance.device_id
        instance.delete()
        _delete_legacy_mirror(make, device_id)

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, pk=None):
        """Full device detail payload (mining, hardware, system, trends for selected window)."""
        device = self.get_object()
        latest_mining = DeviceMiningStats.objects.filter(device=device).first()
        latest_hardware = DeviceHardwareStats.objects.filter(device=device).first()
        latest_system = DeviceSystemInfo.objects.filter(device=device).first()
        # Cap at 90 days to protect large installs; default 24h
        try:
            hours = max(1, min(int(request.query_params.get('hours', 24)), 24 * 90))
        except (TypeError, ValueError):
            hours = 24
        start_time = timezone.now() - timedelta(hours=hours)
        hashrate_trend = list(
            DeviceMiningStats.objects.filter(device=device, recorded_at__gte=start_time)
            .values('recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected')
            .order_by('recorded_at')
        )
        temp_trend = list(
            DeviceHardwareStats.objects.filter(device=device, recorded_at__gte=start_time)
            .values('recorded_at', 'temperature_c', 'power_watts', 'fan_speed_rpm')
            .order_by('recorded_at')
        )

        if device.make == Device.MAKE_AVALON:
            device_data = UnifiedDeviceAsAvalonSerializer(device).data
            mining_ser = UnifiedMiningAsAvalonSerializer
            system_ser = UnifiedSystemAsAvalonSerializer
        else:
            device_data = UnifiedDeviceAsBitaxeSerializer(device).data
            mining_ser = UnifiedMiningAsBitaxeSerializer
            system_ser = UnifiedSystemAsBitaxeSerializer

        return Response({
            'device': device_data,
            'make': device.make,
            'latest_mining': mining_ser(latest_mining).data if latest_mining else None,
            'latest_hardware': UnifiedHardwareSerializer(latest_hardware).data if latest_hardware else None,
            'latest_system': system_ser(latest_system).data if latest_system else None,
            # Keep legacy key names for frontend compatibility
            'hashrate_trend_24h': hashrate_trend,
            'temperature_trend_24h': temp_trend,
            'trend_hours': hours,
        })


class FleetMiningViewSet(viewsets.ReadOnlyModelViewSet):
    """All-device mining stats from unified tables."""
    serializer_class = UnifiedMiningAsBitaxeSerializer

    def get_queryset(self):
        qs = DeviceMiningStats.objects.all().select_related('device')
        make = self.request.query_params.get('make')
        if make:
            qs = qs.filter(device__make=make)
        device_id = self.request.query_params.get('device_id')
        if device_id:
            qs = qs.filter(device__device_id=device_id)
        hours = self.request.query_params.get('hours')
        if hours is not None:
            try:
                h = max(1, min(int(hours), 24 * 90))
                qs = qs.filter(recorded_at__gte=timezone.now() - timedelta(hours=h))
            except (TypeError, ValueError):
                pass
        return qs

    @action(detail=False, methods=['get'])
    def latest(self, request):
        devices = Device.objects.filter(is_active=True)
        make = request.query_params.get('make')
        if make:
            devices = devices.filter(make=make)
        results = []
        for device in devices:
            latest = DeviceMiningStats.objects.filter(device=device).first()
            if not latest:
                continue
            data = UnifiedMiningAsBitaxeSerializer(latest).data
            data['device_type'] = device.make
            data['device_id_str'] = device.device_id
            data['device_name'] = device.name
            data['difficulty'] = latest.best_difficulty
            results.append(data)
        return Response(results)


class FleetHardwareViewSet(viewsets.ReadOnlyModelViewSet):
    """All-device hardware stats from unified tables."""
    serializer_class = UnifiedHardwareSerializer

    def get_queryset(self):
        qs = DeviceHardwareStats.objects.all().select_related('device')
        make = self.request.query_params.get('make')
        if make:
            qs = qs.filter(device__make=make)
        device_id = self.request.query_params.get('device_id')
        if device_id:
            qs = qs.filter(device__device_id=device_id)
        hours = self.request.query_params.get('hours')
        if hours is not None:
            try:
                h = max(1, min(int(hours), 24 * 90))
                qs = qs.filter(recorded_at__gte=timezone.now() - timedelta(hours=h))
            except (TypeError, ValueError):
                pass
        return qs

    @action(detail=False, methods=['get'])
    def latest(self, request):
        devices = Device.objects.filter(is_active=True)
        make = request.query_params.get('make')
        if make:
            devices = devices.filter(make=make)
        results = []
        for device in devices:
            latest = DeviceHardwareStats.objects.filter(device=device).first()
            if not latest:
                continue
            data = UnifiedHardwareSerializer(latest).data
            data['device_type'] = device.make
            data['device_id_str'] = device.device_id
            data['device_name'] = device.name
            results.append(data)
        return Response(results)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_details_by_make_id(request, make, device_id):
    """Device details lookup by make + device_id (for frontend routes)."""
    try:
        device = Device.objects.get(make=make, device_id=device_id)
    except Device.DoesNotExist:
        return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    view = DeviceViewSet()
    view.request = request
    view.format_kwarg = None
    view.kwargs = {'pk': device.pk}
    view.action = 'details'
    return view.details(request, pk=device.pk)


class BitAxeDeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Bitaxe devices with full CRUD operations.
    Dual-writes to the unified Device registry.
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

    def perform_create(self, serializer):
        from .device_sync import sync_bitaxe_to_unified
        instance = serializer.save()
        sync_bitaxe_to_unified(instance)

    def perform_update(self, serializer):
        from .device_sync import sync_bitaxe_to_unified
        instance = serializer.save()
        sync_bitaxe_to_unified(instance)

    def perform_destroy(self, instance):
        from .device_sync import delete_unified_device
        from .models import Device
        device_id = instance.device_id
        instance.delete()
        delete_unified_device(Device.MAKE_BITAXE, device_id)


class BitAxeMiningStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitaxe mining statistics — reads unified device_mining_stats."""
    serializer_class = UnifiedMiningAsBitaxeSerializer

    def get_queryset(self):
        queryset = DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_BITAXE
        ).select_related('device')
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        devices = Device.objects.filter(make=Device.MAKE_BITAXE, is_active=True)
        results = []
        for device in devices:
            latest_stat = DeviceMiningStats.objects.filter(device=device).first()
            if latest_stat:
                results.append(self.get_serializer(latest_stat).data)
        return Response(results)

    @action(detail=False, methods=['get'])
    def hashrate_trend(self, request):
        device_id = request.query_params.get('device_id')
        hours = _parse_int_param(request.query_params.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        start_time = timezone.now() - timedelta(hours=hours)
        queryset = DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_BITAXE,
            recorded_at__gte=start_time,
        )
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        stats = queryset.values(
            'device__name', 'recorded_at', 'hashrate_ghs',
            'shares_accepted', 'shares_rejected',
        ).order_by('recorded_at')
        # Alias device__name → device__device_name for frontend compatibility
        out = []
        for row in stats:
            out.append({
                'device__device_name': row['device__name'],
                'recorded_at': row['recorded_at'],
                'hashrate_ghs': row['hashrate_ghs'],
                'shares_accepted': row['shares_accepted'],
                'shares_rejected': row['shares_rejected'],
            })
        return Response(out)


class BitAxeHardwareLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitaxe hardware logs — reads unified device_hardware_stats."""
    serializer_class = UnifiedHardwareSerializer

    def get_queryset(self):
        queryset = DeviceHardwareStats.objects.filter(
            device__make=Device.MAKE_BITAXE
        ).select_related('device')
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        devices = Device.objects.filter(make=Device.MAKE_BITAXE, is_active=True)
        results = []
        for device in devices:
            latest_log = DeviceHardwareStats.objects.filter(device=device).first()
            if latest_log:
                results.append(self.get_serializer(latest_log).data)
        return Response(results)

    @action(detail=False, methods=['get'])
    def temperature_trend(self, request):
        device_id = request.query_params.get('device_id')
        hours = _parse_int_param(request.query_params.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        start_time = timezone.now() - timedelta(hours=hours)
        queryset = DeviceHardwareStats.objects.filter(
            device__make=Device.MAKE_BITAXE,
            recorded_at__gte=start_time,
        )
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        logs = queryset.values(
            'device__name', 'recorded_at', 'temperature_c',
            'power_watts', 'fan_speed_rpm',
        ).order_by('recorded_at')
        out = [
            {
                'device__device_name': row['device__name'],
                'recorded_at': row['recorded_at'],
                'temperature_c': row['temperature_c'],
                'power_watts': row['power_watts'],
                'fan_speed_rpm': row['fan_speed_rpm'],
            }
            for row in logs
        ]
        return Response(out)


class BitAxeSystemInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitaxe system info — reads unified device_system_info."""
    serializer_class = UnifiedSystemAsBitaxeSerializer

    def get_queryset(self):
        queryset = DeviceSystemInfo.objects.filter(
            device__make=Device.MAKE_BITAXE
        ).select_related('device')
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device__device_id=device_id)
        return queryset

    @action(detail=False, methods=['get'], url_path='device/(?P<device_id>[^/.]+)')
    def device_details(self, request, device_id=None):
        """Get complete device details including latest stats, hardware, and system info."""
        try:
            device = Device.objects.get(make=Device.MAKE_BITAXE, device_id=device_id)
        except Device.DoesNotExist:
            # Fallback: legacy registry still present during dual-registry era
            try:
                legacy = BitAxeDevice.objects.get(device_id=device_id)
            except BitAxeDevice.DoesNotExist:
                return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                'device': BitAxeDeviceSerializer(legacy).data,
                'latest_mining': None,
                'latest_hardware': None,
                'latest_system': None,
                'hashrate_trend_24h': [],
                'temperature_trend_24h': [],
            })

        latest_mining = DeviceMiningStats.objects.filter(device=device).first()
        latest_hardware = DeviceHardwareStats.objects.filter(device=device).first()
        latest_system = DeviceSystemInfo.objects.filter(device=device).first()

        try:
            hours = max(1, min(int(request.query_params.get('hours', 24)), 24 * 90))
        except (TypeError, ValueError):
            hours = 24
        start_time = timezone.now() - timedelta(hours=hours)
        hashrate_trend = DeviceMiningStats.objects.filter(
            device=device, recorded_at__gte=start_time
        ).values('recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected').order_by('recorded_at')

        temp_trend = DeviceHardwareStats.objects.filter(
            device=device, recorded_at__gte=start_time
        ).values('recorded_at', 'temperature_c', 'power_watts', 'fan_speed_rpm').order_by('recorded_at')

        return Response({
            'device': UnifiedDeviceAsBitaxeSerializer(device).data,
            'latest_mining': UnifiedMiningAsBitaxeSerializer(latest_mining).data if latest_mining else None,
            'latest_hardware': UnifiedHardwareSerializer(latest_hardware).data if latest_hardware else None,
            'latest_system': UnifiedSystemAsBitaxeSerializer(latest_system).data if latest_system else None,
            'hashrate_trend_24h': list(hashrate_trend),
            'temperature_trend_24h': list(temp_trend),
            'trend_hours': hours,
        })


class BitAxePoolStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """Pool statistics — reads unified pool_stats with legacy field aliases."""
    serializer_class = UnifiedPoolAsLegacySerializer

    def get_queryset(self):
        queryset = PoolStats.objects.all()
        pool_address = self.request.query_params.get('pool_address')
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        hours = self.request.query_params.get('hours')
        if hours is not None:
            try:
                h = max(1, min(int(hours), 24 * 90))
                queryset = queryset.filter(
                    recorded_at__gte=timezone.now() - timedelta(hours=h)
                )
            except (TypeError, ValueError):
                pass
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        pool_address = request.query_params.get('pool_address')
        qs = PoolStats.objects.all()
        if pool_address:
            qs = qs.filter(pool_address=pool_address)
        latest_stat = qs.first()
        if latest_stat:
            return Response(self.get_serializer(latest_stat).data)
        return Response({'detail': 'No pool statistics found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def hashrate_trend(self, request):
        pool_address = request.query_params.get('pool_address')
        hours = _parse_int_param(request.query_params.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        start_time = timezone.now() - timedelta(hours=hours)
        queryset = PoolStats.objects.filter(recorded_at__gte=start_time)
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        stats = queryset.values(
            'recorded_at', 'hashrate_1m_display', 'hashrate_5m_display',
            'hashrate_1h_display', 'hashrate_1d_display',
            'hashrate_1m_ghs', 'hashrate_1d_ghs', 'shares', 'workers', 'best_share',
        ).order_by('recorded_at')
        out = [
            {
                'recorded_at': row['recorded_at'],
                'hashrate_1m': row['hashrate_1m_display'],
                'hashrate_5m': row['hashrate_5m_display'],
                'hashrate_1hr': row['hashrate_1h_display'],
                'hashrate_1d': row['hashrate_1d_display'],
                'hashrate_1m_ghs': row['hashrate_1m_ghs'],
                'hashrate_1d_ghs': row['hashrate_1d_ghs'],
                'shares': row['shares'],
                'workers': row['workers'],
                # Legacy frontend aliases
                'bestshare': row['best_share'],
                'best_share': row['best_share'],
            }
            for row in stats
        ]
        return Response(out)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        pool_address = request.query_params.get('pool_address')
        days = _parse_int_param(request.query_params.get('days', 7), 7, min_value=1, max_value=_MAX_DAYS)
        start_date = timezone.now() - timedelta(days=days)
        queryset = PoolStats.objects.filter(recorded_at__gte=start_date)
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
            best_share=Max('best_share'),
            data_points=Count('id'),
        )
        first_record = queryset.order_by('recorded_at').first()
        latest_record = queryset.order_by('-recorded_at').first()
        if first_record and latest_record and first_record.shares is not None and latest_record.shares is not None:
            stats['total_shares'] = latest_record.shares - first_record.shares
        else:
            stats['total_shares'] = 0
        return Response(stats)



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

