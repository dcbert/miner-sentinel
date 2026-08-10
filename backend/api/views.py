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
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)
from .serializers import (
    BitaxeDeviceWriteSerializer,
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
from .time_window import MAX_DAYS as _MAX_DAYS
from .time_window import MAX_HOURS as _MAX_HOURS
from .time_window import parse_int_param as _parse_int_param
from .time_window import parse_time_window

logger = logging.getLogger(__name__)


class DeviceViewSet(viewsets.ModelViewSet):
    """Unified device registry CRUD (sole device store after Release C)."""
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

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, pk=None):
        """Full device detail payload (mining, hardware, system, trends for selected window)."""
        device = self.get_object()
        latest_mining = DeviceMiningStats.objects.filter(device=device).first()
        latest_hardware = DeviceHardwareStats.objects.filter(device=device).first()
        latest_system = DeviceSystemInfo.objects.filter(device=device).first()
        window = parse_time_window(request.query_params)
        time_filter = window.as_filter()
        hashrate_trend = list(
            DeviceMiningStats.objects.filter(device=device, **time_filter)
            .values('recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected')
            .order_by('recorded_at')
        )
        temp_trend = list(
            DeviceHardwareStats.objects.filter(device=device, **time_filter)
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
            'trend_hours': window.hours,
            'window_start': window.start.isoformat(),
            'window_end': window.end.isoformat(),
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
        params = self.request.query_params
        if any(params.get(k) not in (None, '') for k in ('hours', 'days', 'from', 'to')):
            window = parse_time_window(params)
            qs = qs.filter(**window.as_filter())
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
        params = self.request.query_params
        if any(params.get(k) not in (None, '') for k in ('hours', 'days', 'from', 'to')):
            window = parse_time_window(params)
            qs = qs.filter(**window.as_filter())
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
    Legacy URL shim: Bitaxe device CRUD against unified Device (make=bitaxe).
    """
    lookup_field = 'device_id'

    def get_queryset(self):
        queryset = Device.objects.filter(make=Device.MAKE_BITAXE).order_by('name')
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BitaxeDeviceWriteSerializer
        return UnifiedDeviceAsBitaxeSerializer


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
        window = parse_time_window(request.query_params)
        queryset = DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_BITAXE,
            **window.as_filter(),
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
        window = parse_time_window(request.query_params)
        queryset = DeviceHardwareStats.objects.filter(
            device__make=Device.MAKE_BITAXE,
            **window.as_filter(),
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
            return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        latest_mining = DeviceMiningStats.objects.filter(device=device).first()
        latest_hardware = DeviceHardwareStats.objects.filter(device=device).first()
        latest_system = DeviceSystemInfo.objects.filter(device=device).first()

        window = parse_time_window(request.query_params)
        time_filter = window.as_filter()
        hashrate_trend = DeviceMiningStats.objects.filter(
            device=device, **time_filter
        ).values('recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected').order_by('recorded_at')

        temp_trend = DeviceHardwareStats.objects.filter(
            device=device, **time_filter
        ).values('recorded_at', 'temperature_c', 'power_watts', 'fan_speed_rpm').order_by('recorded_at')

        return Response({
            'device': UnifiedDeviceAsBitaxeSerializer(device).data,
            'latest_mining': UnifiedMiningAsBitaxeSerializer(latest_mining).data if latest_mining else None,
            'latest_hardware': UnifiedHardwareSerializer(latest_hardware).data if latest_hardware else None,
            'latest_system': UnifiedSystemAsBitaxeSerializer(latest_system).data if latest_system else None,
            'hashrate_trend_24h': list(hashrate_trend),
            'temperature_trend_24h': list(temp_trend),
            'trend_hours': window.hours,
            'window_start': window.start.isoformat(),
            'window_end': window.end.isoformat(),
        })


class PoolStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    First-class pool statistics API (/api/pool/).
    Reads unified pool_stats; supports pool_type + pool_address filters.
    """
    serializer_class = UnifiedPoolAsLegacySerializer

    def get_queryset(self):
        queryset = PoolStats.objects.all()
        pool_address = self.request.query_params.get('pool_address')
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        pool_type = self.request.query_params.get('pool_type')
        if pool_type:
            queryset = queryset.filter(pool_type=pool_type)
        params = self.request.query_params
        if any(params.get(k) not in (None, '') for k in ('hours', 'days', 'from', 'to')):
            window = parse_time_window(params)
            queryset = queryset.filter(**window.as_filter())
        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        pool_address = request.query_params.get('pool_address')
        pool_type = request.query_params.get('pool_type')
        qs = PoolStats.objects.all().order_by('-recorded_at')
        if pool_address:
            qs = qs.filter(pool_address=pool_address)
        if pool_type:
            qs = qs.filter(pool_type=pool_type)
        latest_stat = qs.first()
        if latest_stat:
            return Response(self.get_serializer(latest_stat).data)
        return Response({'detail': 'No pool statistics found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def hashrate_trend(self, request):
        pool_address = request.query_params.get('pool_address')
        pool_type = request.query_params.get('pool_type')
        window = parse_time_window(request.query_params)
        queryset = PoolStats.objects.filter(**window.as_filter())
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        if pool_type:
            queryset = queryset.filter(pool_type=pool_type)
        stats = queryset.values(
            'recorded_at', 'hashrate_1m_display', 'hashrate_5m_display',
            'hashrate_1h_display', 'hashrate_1d_display',
            'hashrate_1m_ghs', 'hashrate_1d_ghs', 'shares', 'workers', 'best_share',
            'pool_type', 'pool_address',
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
                'bestshare': row['best_share'],
                'best_share': row['best_share'],
                'pool_type': row['pool_type'],
                'pool_address': row['pool_address'],
            }
            for row in stats
        ]
        return Response(out)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        pool_address = request.query_params.get('pool_address')
        pool_type = request.query_params.get('pool_type')
        window = parse_time_window(request.query_params)
        queryset = PoolStats.objects.filter(**window.as_filter())
        if pool_address:
            queryset = queryset.filter(pool_address=pool_address)
        if pool_type:
            queryset = queryset.filter(pool_type=pool_type)

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


class BitAxePoolStatsViewSet(PoolStatsViewSet):
    """Legacy URL alias for /api/bitaxe/pool/ → same as /api/pool/."""
    pass



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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_telegram_notification(request):
    """Send a test Telegram message using stored credentials."""
    import requests as http_requests

    settings = CollectorSettings.get_settings()
    token = (settings.telegram_bot_token or '').strip()
    chat_id = (settings.telegram_chat_id or '').strip()
    # Allow one-off token/chat from body without persisting
    body = request.data or {}
    if body.get('telegram_bot_token'):
        token = str(body['telegram_bot_token']).strip()
    if body.get('telegram_chat_id'):
        chat_id = str(body['telegram_chat_id']).strip()

    if not token or not chat_id:
        return Response(
            {'success': False, 'error': 'Telegram bot token and chat ID are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not settings.telegram_enabled and not body.get('force'):
        return Response(
            {
                'success': False,
                'error': 'Telegram channel is disabled. Enable it or pass force=true to test.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resp = http_requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': (
                    '✅ <b>MinerSentinel test</b>\n\n'
                    'Telegram notifications are working correctly.'
                ),
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
            timeout=15,
        )
        data = resp.json() if resp.content else {}
        if resp.ok and data.get('ok'):
            return Response({'success': True, 'message': 'Test message sent to Telegram'})
        return Response(
            {
                'success': False,
                'error': data.get('description') or f'Telegram API error ({resp.status_code})',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Telegram test failed: {e}", exc_info=True)
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_discord_notification(request):
    """Send a test Discord webhook embed using stored credentials."""
    import requests as http_requests

    settings = CollectorSettings.get_settings()
    webhook = (settings.discord_webhook_url or '').strip()
    body = request.data or {}
    if body.get('discord_webhook_url'):
        webhook = str(body['discord_webhook_url']).strip()

    if not webhook:
        return Response(
            {'success': False, 'error': 'Discord webhook URL is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not settings.discord_enabled and not body.get('force'):
        return Response(
            {
                'success': False,
                'error': 'Discord channel is disabled. Enable it or pass force=true to test.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        resp = http_requests.post(
            webhook,
            json={
                'username': 'MinerSentinel',
                'embeds': [
                    {
                        'title': '✅ MinerSentinel test',
                        'description': 'Discord webhook notifications are working correctly.',
                        'color': 3066993,
                    }
                ],
            },
            timeout=15,
        )
        if resp.status_code in (200, 204):
            return Response({'success': True, 'message': 'Test message sent to Discord'})
        return Response(
            {
                'success': False,
                'error': f'Discord webhook error ({resp.status_code}): {resp.text[:200]}',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Discord test failed: {e}", exc_info=True)
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_502_BAD_GATEWAY,
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

