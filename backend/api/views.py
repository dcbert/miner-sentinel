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
    AlertEvent,
    CollectorSettings,
    Device,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)
from .serializers import (
    AlertEventSerializer,
    CollectorSettingsSerializer,
    DeviceSerializer,
    DeviceWriteSerializer,
)
from .unified_serializers import (
    UnifiedHardwareSerializer,
    UnifiedMiningSerializer,
    UnifiedPoolSerializer,
    UnifiedSystemSerializer,
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

        return Response({
            'device': DeviceSerializer(device).data,
            'make': device.make,
            'latest_mining': UnifiedMiningSerializer(latest_mining).data if latest_mining else None,
            'latest_hardware': UnifiedHardwareSerializer(latest_hardware).data if latest_hardware else None,
            'latest_system': UnifiedSystemSerializer(latest_system).data if latest_system else None,
            # Keep stable key names for frontend detail charts
            'hashrate_trend_24h': hashrate_trend,
            'temperature_trend_24h': temp_trend,
            'trend_hours': window.hours,
            'window_start': window.start.isoformat(),
            'window_end': window.end.isoformat(),
        })


class FleetMiningViewSet(viewsets.ReadOnlyModelViewSet):
    """All-device mining stats from unified tables."""
    serializer_class = UnifiedMiningSerializer

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
            data = UnifiedMiningSerializer(latest).data
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


class PoolStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Pool statistics API (/api/pool/).
    Reads unified pool_stats; supports pool_type + pool_address filters.
    """
    serializer_class = UnifiedPoolSerializer

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_push_notification(request):
    """Send a test message via ntfy / Gotify / generic webhook using stored settings."""
    import requests as http_requests

    settings = CollectorSettings.get_settings()
    body = request.data or {}
    channel = (body.get('channel') or 'auto').strip().lower()

    ntfy_url = (body.get('ntfy_url') or settings.ntfy_url or '').strip()
    ntfy_token = (body.get('ntfy_token') or settings.ntfy_token or '').strip()
    gotify_url = (body.get('gotify_url') or settings.gotify_url or '').strip().rstrip('/')
    gotify_token = (body.get('gotify_token') or settings.gotify_token or '').strip()
    webhook_url = (body.get('webhook_url') or settings.webhook_url or '').strip()

    ntfy_on = settings.ntfy_enabled or channel == 'ntfy' or body.get('force')
    gotify_on = settings.gotify_enabled or channel == 'gotify' or body.get('force')
    webhook_on = settings.webhook_enabled or channel == 'webhook' or body.get('force')

    if channel == 'ntfy':
        gotify_on = webhook_on = False
        ntfy_on = True
    elif channel == 'gotify':
        ntfy_on = webhook_on = False
        gotify_on = True
    elif channel == 'webhook':
        ntfy_on = gotify_on = False
        webhook_on = True

    sent = []
    errors = []

    if ntfy_on and ntfy_url:
        try:
            headers = {'Title': 'MinerSentinel test', 'Priority': '3', 'Tags': 'white_check_mark'}
            if ntfy_token:
                headers['Authorization'] = f'Bearer {ntfy_token}'
            resp = http_requests.post(
                ntfy_url,
                data=b'ntfy push notifications are working correctly for MinerSentinel.',
                headers=headers,
                timeout=15,
            )
            if resp.ok:
                sent.append('ntfy')
            else:
                errors.append(f'ntfy ({resp.status_code}): {resp.text[:160]}')
        except Exception as e:
            errors.append(f'ntfy: {e}')
    elif channel == 'ntfy':
        errors.append('ntfy topic URL is required')

    if gotify_on and gotify_url and gotify_token:
        try:
            resp = http_requests.post(
                f'{gotify_url}/message',
                params={'token': gotify_token},
                json={
                    'title': 'MinerSentinel test',
                    'message': 'Gotify notifications are working correctly for MinerSentinel.',
                    'priority': 3,
                },
                timeout=15,
            )
            if resp.ok:
                sent.append('gotify')
            else:
                errors.append(f'gotify ({resp.status_code}): {resp.text[:160]}')
        except Exception as e:
            errors.append(f'gotify: {e}')
    elif channel == 'gotify':
        errors.append('Gotify URL and token are required')

    if webhook_on and webhook_url:
        try:
            resp = http_requests.post(
                webhook_url,
                json={
                    'source': 'minersentinel',
                    'title': 'MinerSentinel test',
                    'message': 'Generic webhook notifications are working correctly.',
                    'severity': 'info',
                    'event_key': 'test',
                },
                timeout=15,
            )
            if resp.ok:
                sent.append('webhook')
            else:
                errors.append(f'webhook ({resp.status_code}): {resp.text[:160]}')
        except Exception as e:
            errors.append(f'webhook: {e}')
    elif channel == 'webhook':
        errors.append('Webhook URL is required')

    if not sent and not errors:
        return Response(
            {
                'success': False,
                'error': 'Enable ntfy, Gotify, or a webhook and provide a URL (or pass force=true).',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if sent and not errors:
        return Response({'success': True, 'message': f'Test sent via {", ".join(sent)}'})
    if sent and errors:
        return Response(
            {
                'success': True,
                'message': f'Partial success via {", ".join(sent)}; errors: {"; ".join(errors)}',
            }
        )
    return Response(
        {'success': False, 'error': '; '.join(errors)},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ---------------------------------------------------------------------------
# Device control (MinerWatch-style) — proxies to data-service LAN adapters
# ---------------------------------------------------------------------------

CONTROL_CAPABILITIES = {
    'bitaxe': {
        'reboot': True, 'fan': True, 'frequency': True, 'voltage': True,
        'pause': True, 'resume': True, 'set_pool': True, 'workmode': False,
    },
    'avalon': {
        'reboot': True, 'fan': True, 'frequency': False, 'voltage': False,
        'pause': False, 'resume': False, 'set_pool': False, 'workmode': True,
    },
    'nmaxe': {
        'reboot': True, 'fan': True, 'frequency': True, 'voltage': True,
        'pause': False, 'resume': False, 'set_pool': True, 'workmode': False,
    },
    'nerdnos': {
        'reboot': False, 'fan': False, 'frequency': False, 'voltage': False,
        'pause': False, 'resume': False, 'set_pool': False, 'workmode': False,
    },
}

CONTROL_CONFIRM_ACTIONS = frozenset({'reboot', 'set_pool', 'workmode'})


def _data_service_url():
    import os
    return os.environ.get('DATA_SERVICE_URL', 'http://data-service:5000')


def _log_control_event(device, action, success, result=None, error=None, user=None):
    """Persist control action to AlertEvent when the model is available."""
    event_type_map = {
        'reboot': 'user_reboot',
        'fan': 'fan_changed',
        'frequency': 'frequency_changed',
        'voltage': 'voltage_changed',
        'pause': 'mining_paused',
        'resume': 'mining_resumed',
        'set_pool': 'pool_changed',
        'workmode': 'workmode_changed',
    }
    event_type = event_type_map.get(action, f'control_{action}')
    severity = AlertEvent.SEVERITY_INFO if success else AlertEvent.SEVERITY_WARN
    msg = (
        f"{'OK' if success else 'FAILED'}: {action} on "
        f"{device.name} ({device.make}:{device.device_id})"
    )
    if error:
        msg = f"{msg} — {error}"
    payload = {
        'action': action,
        'success': success,
        'result': result if isinstance(result, dict) else {},
        'error': error,
        'user': getattr(user, 'username', None),
    }
    try:
        make = getattr(device, 'make', '') or ''
        key = getattr(device, 'device_id', '') or ''
        AlertEvent.objects.create(
            event_type=event_type,
            severity=severity,
            device=device,
            device_make=make,
            device_key=key,
            device_name=getattr(device, 'name', '') or '',
            message=msg,
            payload=payload,
            fingerprint=f"{event_type}:{make}:{key}"[:191],
        )
    except Exception as e:  # noqa: BLE001 — never fail control response on audit write
        # Keep control path resilient if schema lags
        logger.warning('Could not persist control AlertEvent: %s', e)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_capabilities(request, make, device_id):
    """Capability-gated control map for a device."""
    try:
        device = Device.objects.get(make=make, device_id=device_id)
    except Device.DoesNotExist:
        return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    caps = dict(CONTROL_CAPABILITIES.get(device.make, {}))
    if not caps:
        caps = {k: False for k in (
            'reboot', 'fan', 'frequency', 'voltage', 'pause', 'resume', 'set_pool', 'workmode',
        )}

    from .lib.devices_status import is_device_online_server
    online = is_device_online_server(device)

    return Response({
        'make': device.make,
        'device_id': device.device_id,
        'offline': not online,
        'capabilities': caps,
        'confirm_actions': sorted(CONTROL_CONFIRM_ACTIONS),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def device_control(request, make, device_id):
    """
    POST /api/devices/{make}/{device_id}/control/
    Body: { "action": "reboot"|"fan"|..., "params": {...} }
    """
    import requests

    try:
        device = Device.objects.get(make=make, device_id=device_id)
    except Device.DoesNotExist:
        return Response({'detail': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    body = request.data or {}
    action = str(body.get('action') or '').strip().lower()
    params = body.get('params') if isinstance(body.get('params'), dict) else {}

    if not action:
        return Response({'error': 'action is required'}, status=status.HTTP_400_BAD_REQUEST)

    caps = CONTROL_CAPABILITIES.get(device.make, {})
    if not caps.get(action):
        return Response(
            {'error': f'Action "{action}" is not supported for {device.make}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .lib.devices_status import is_device_online_server
    if not is_device_online_server(device):
        return Response(
            {'error': 'Device appears offline — controls are disabled'},
            status=status.HTTP_409_CONFLICT,
        )

    try:
        resp = requests.post(
            f'{_data_service_url()}/control',
            json={
                'make': device.make,
                'device_id': device.device_id,
                'action': action,
                'params': params,
            },
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        logger.error('Control proxy failed: %s', e)
        _log_control_event(device, action, False, error='data-service unavailable', user=request.user)
        return Response(
            {'error': 'Data collector service unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        data = {'ok': False, 'error': resp.text[:300]}

    success = resp.ok and data.get('ok', False)
    _log_control_event(
        device,
        action,
        success,
        result=data if success else None,
        error=None if success else data.get('error') or f'HTTP {resp.status_code}',
        user=request.user,
    )

    if success:
        return Response(data)
    status_code = resp.status_code if resp.status_code >= 400 else status.HTTP_502_BAD_GATEWAY
    return Response(data, status=status_code)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def discover_devices_view(request):
    """Proxy LAN discovery to data-service."""
    import requests

    body = request.data or {}
    try:
        resp = requests.post(
            f'{_data_service_url()}/discover',
            json={
                'cidr': body.get('cidr'),
                'seed_ips': body.get('seed_ips'),
            },
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        logger.error('Discovery proxy failed: %s', e)
        return Response(
            {'error': 'Data collector service unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        return Response({'error': 'Invalid discovery response'}, status=status.HTTP_502_BAD_GATEWAY)

    # Annotate which discovered IPs are already registered
    registered = {
        (d.make, d.ip_address): d
        for d in Device.objects.filter(is_active=True)
    }
    for item in data.get('devices') or []:
        key = (item.get('make'), item.get('ip_address'))
        existing = registered.get(key)
        item['already_registered'] = bool(existing)
        if existing:
            item['registered_device_id'] = existing.device_id
            item['registered_name'] = existing.name

    return Response(data, status=resp.status_code if not resp.ok else status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def advisor_view(request):
    """
    Ranked next-actions with one-click control hooks where possible.
    Lightweight Phase 3 advisor (does not replace Overview open-problems strip).
    """
    suggestions = []
    now = timezone.now()

    for device in Device.objects.filter(is_active=True).order_by('name'):
        caps = CONTROL_CAPABILITIES.get(device.make, {})
        age = None
        if device.last_seen_at:
            age = (now - device.last_seen_at).total_seconds()

        offline = bool(device.error_message) or age is None or (age is not None and age > 600)
        if offline and caps.get('reboot'):
            suggestions.append({
                'priority': 10 if age is None or age > 3600 else 20,
                'kind': 'device_offline',
                'title': f'{device.name} appears offline',
                'detail': device.error_message or 'No recent successful poll',
                'device': {'make': device.make, 'device_id': device.device_id, 'name': device.name},
                'actions': [
                    {
                        'label': 'Reboot',
                        'control': {'action': 'reboot', 'params': {}},
                        'confirm': True,
                    },
                ],
            })

        latest_hw = DeviceHardwareStats.objects.filter(device=device).first()
        if latest_hw and latest_hw.temperature_c and latest_hw.temperature_c >= 85 and caps.get('fan'):
            suggestions.append({
                'priority': 15,
                'kind': 'high_temp',
                'title': f'{device.name} at {latest_hw.temperature_c:.0f}°C',
                'detail': 'Raise fan speed to cool the miner',
                'device': {'make': device.make, 'device_id': device.device_id, 'name': device.name},
                'actions': [
                    {
                        'label': 'Fan 100%',
                        'control': {'action': 'fan', 'params': {'percent': 100, 'auto': False}},
                        'confirm': False,
                    },
                ],
            })

        if device.make == 'avalon' and caps.get('workmode') and not offline:
            suggestions.append({
                'priority': 80,
                'kind': 'avalon_workmode',
                'title': f'{device.name}: Avalon workmode',
                'detail': 'Switch Low / Mid / High power preset',
                'device': {'make': device.make, 'device_id': device.device_id, 'name': device.name},
                'actions': [
                    {'label': 'Low', 'control': {'action': 'workmode', 'params': {'mode': 0}}, 'confirm': True},
                    {'label': 'Mid', 'control': {'action': 'workmode', 'params': {'mode': 1}}, 'confirm': True},
                    {'label': 'High', 'control': {'action': 'workmode', 'params': {'mode': 2}}, 'confirm': True},
                ],
            })

    settings = CollectorSettings.get_settings()
    if not settings.telegram_enabled and not settings.discord_enabled:
        suggestions.append({
            'priority': 50,
            'kind': 'alerts_not_configured',
            'title': 'Alerts not configured',
            'detail': 'Enable Telegram or Discord in Settings → Notifications',
            'device': None,
            'actions': [],
            'href': '/settings',
        })

    suggestions.sort(key=lambda s: s['priority'])
    return Response({'suggestions': suggestions[:20]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_inventory_csv(request):
    """Phase 4 foundation: export device inventory (+ optional alert history) as CSV."""
    import csv
    from io import StringIO

    from django.http import HttpResponse

    include_alerts = str(request.query_params.get('alerts', 'false')).lower() == 'true'
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'make', 'device_id', 'name', 'ip_address', 'port', 'protocol',
        'model', 'is_active', 'last_seen_at', 'error_message',
    ])
    for d in Device.objects.all().order_by('make', 'name'):
        writer.writerow([
            d.make, d.device_id, d.name, d.ip_address, d.port or '',
            d.protocol, d.model or '', d.is_active,
            d.last_seen_at.isoformat() if d.last_seen_at else '',
            (d.error_message or '').replace('\n', ' ')[:500],
        ])

    if include_alerts:
        writer.writerow([])
        writer.writerow(['event_type', 'severity', 'device_make', 'device_id', 'message', 'created_at', 'acknowledged_at'])
        for ev in AlertEvent.objects.select_related('device').order_by('-created_at')[:5000]:
            writer.writerow([
                ev.event_type,
                ev.severity,
                ev.device.make if ev.device else '',
                ev.device.device_id if ev.device else '',
                (ev.message or '').replace('\n', ' ')[:500],
                ev.created_at.isoformat() if ev.created_at else '',
                ev.acknowledged_at.isoformat() if ev.acknowledged_at else '',
            ])

    resp = HttpResponse(buf.getvalue(), content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="minersentinel-inventory.csv"'
    return resp


# Push channel status (ntfy / Gotify / webhook live; Web Push VAPID optional/deferred)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def push_channels_status(request):
    """Report configured push delivery channels (no secrets)."""
    settings = CollectorSettings.get_settings()
    ntfy_ready = bool(settings.ntfy_enabled and (settings.ntfy_url or '').strip())
    gotify_ready = bool(
        settings.gotify_enabled
        and (settings.gotify_url or '').strip()
        and (settings.gotify_token or '').strip()
    )
    webhook_ready = bool(settings.webhook_enabled and (settings.webhook_url or '').strip())
    return Response({
        'web_push': {
            'available': False,
            'status': 'deferred',
            'message': 'Browser Web Push (VAPID) deferred — use ntfy on Umbrel/LAN',
        },
        'ntfy': {
            'available': True,
            'status': 'ready' if ntfy_ready else 'configured' if (settings.ntfy_url or '').strip() else 'off',
            'enabled': settings.ntfy_enabled,
            'url_configured': bool((settings.ntfy_url or '').strip()),
            'token_configured': bool((settings.ntfy_token or '').strip()),
            'message': 'POST to topic URL (ntfy.sh or self-hosted)',
        },
        'gotify': {
            'available': True,
            'status': 'ready' if gotify_ready else 'off',
            'enabled': settings.gotify_enabled,
            'url_configured': bool((settings.gotify_url or '').strip()),
            'token_configured': bool((settings.gotify_token or '').strip()),
            'message': 'Gotify /message with app token',
        },
        'webhook': {
            'available': True,
            'status': 'ready' if webhook_ready else 'off',
            'enabled': settings.webhook_enabled,
            'url_configured': bool((settings.webhook_url or '').strip()),
            'message': 'Generic JSON POST {title, message, severity, event_key}',
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stratum_pool_compare(request):
    """
    Side-by-side: each device's primary/fallback stratum vs selected pool stats.
    Does not poll every pool type concurrently — uses configured pool_type + latest sample.
    """
    settings = CollectorSettings.get_settings()
    pool_type = settings.pool_type or 'ckpool'
    address_field = {
        'ckpool': 'ckpool_address',
        'publicpool': 'publicpool_address',
        'btcpowlab': 'btcpowlab_address',
        'parasite': 'parasite_address',
    }.get(pool_type, 'ckpool_address')
    configured_address = getattr(settings, address_field, '') or ''

    latest = PoolStats.objects.filter(pool_type=pool_type).order_by('-recorded_at').first()
    selected_pool = {
        'pool_type': pool_type,
        'configured_address': configured_address,
        'latest': UnifiedPoolSerializer(latest).data if latest else None,
    }

    devices = []
    for device in Device.objects.filter(is_active=True).order_by('make', 'name'):
        sysinfo = DeviceSystemInfo.objects.filter(device=device).order_by('-recorded_at').first()
        primary = (sysinfo.primary_pool_url if sysinfo else None) or ''
        fallback = (sysinfo.fallback_pool_url if sysinfo else None) or ''
        devices.append({
            'id': device.id,
            'device_id': device.device_id,
            'name': device.name,
            'make': device.make,
            'primary_pool_url': primary or None,
            'primary_pool_user': sysinfo.primary_pool_user if sysinfo else None,
            'fallback_pool_url': fallback or None,
            'fallback_pool_user': sysinfo.fallback_pool_user if sysinfo else None,
            'using_fallback': sysinfo.using_fallback_pool if sysinfo else None,
            'stratum_host': _stratum_host(primary),
            'matches_selected_pool_type': _stratum_hints_pool_type(primary, pool_type),
        })

    return Response({
        'selected_pool': selected_pool,
        'devices': devices,
    })


def _stratum_host(url: str) -> str:
    if not url:
        return ''
    raw = url.replace('stratum+tcp://', '').replace('stratum+ssl://', '').replace('stratum://', '')
    return raw.split('/')[0].split(':')[0].lower()


def _stratum_hints_pool_type(url: str, pool_type: str) -> bool | None:
    """Best-effort host keyword match; None when unknown."""
    host = _stratum_host(url)
    if not host:
        return None
    hints = {
        'ckpool': ('ckpool', 'solo.ckpool', 'eusolo'),
        'publicpool': ('public-pool', 'publicpool'),
        'btcpowlab': ('btcpowlab',),
        'parasite': ('parasite',),
    }
    keys = hints.get(pool_type) or ()
    return any(k in host for k in keys) if keys else None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def collector_status_view(request):
    """Proxy data-service /status for honest collector health in Settings + Overview."""
    import requests

    data_service_url = _data_service_url()
    try:
        response = requests.get(f'{data_service_url}/status', timeout=5)
        if response.ok:
            data = response.json()
            data['reachable'] = True
            return Response(data)
        return Response(
            {
                'reachable': False,
                'status': 'unreachable',
                'error': f'Data service returned {response.status_code}',
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f'Collector status unreachable: {e}')
        return Response(
            {
                'reachable': False,
                'status': 'unreachable',
                'error': 'Data collector service unavailable',
                'last_success_at': None,
                'next_run': None,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_events_list(request):
    """Activity / alert journal feed.

    kind=problem — warn/critical needing attention (default when open=true)
    kind=highlight — celebrations / info / control audits
    kind=all — everything
    """
    HIGHLIGHT_TYPES = ('best_difficulty', 'device_online')
    PROBLEM_TYPES = (
        'device_offline',
        'hashrate_stagnation',
        'auto_restart',
        'temperature_high',
        'fan_dead',
        'pool_down',
        'collector_down',
        'expected_hashrate_drop',
    )

    # One-time cleanup: leftover highlight rows must not linger as "open problems"
    AlertEvent.objects.filter(
        event_type__in=HIGHLIGHT_TYPES,
        acknowledged_at__isnull=True,
        resolved_at__isnull=True,
    ).update(acknowledged_at=timezone.now())

    qs = AlertEvent.objects.all().order_by('-created_at')
    open_only = str(request.query_params.get('open', '')).lower() in ('1', 'true', 'yes')
    kind = (request.query_params.get('kind') or '').lower()
    if not kind:
        kind = 'problem' if open_only else 'all'

    if open_only:
        qs = qs.filter(resolved_at__isnull=True, acknowledged_at__isnull=True)

    if kind == 'problem':
        qs = qs.filter(
            Q(severity__in=(AlertEvent.SEVERITY_WARN, AlertEvent.SEVERITY_CRITICAL))
            | Q(event_type__in=PROBLEM_TYPES)
        ).exclude(event_type__in=HIGHLIGHT_TYPES).exclude(event_type__startswith='user_')
    elif kind == 'highlight':
        qs = qs.filter(
            Q(event_type__in=HIGHLIGHT_TYPES)
            | Q(event_type__startswith='user_')
            | Q(severity=AlertEvent.SEVERITY_INFO)
        )

    severity = request.query_params.get('severity')
    if severity in ('info', 'warn', 'critical'):
        qs = qs.filter(severity=severity)

    event_type = request.query_params.get('event_type')
    if event_type:
        qs = qs.filter(event_type=event_type)

    device_make = request.query_params.get('make')
    device_key = request.query_params.get('device_id')
    if device_make:
        qs = qs.filter(Q(device_make=device_make) | Q(device__make=device_make))
    if device_key:
        qs = qs.filter(Q(device_key=device_key) | Q(device__device_id=device_key))

    try:
        limit = min(int(request.query_params.get('limit', 50)), 200)
    except (TypeError, ValueError):
        limit = 50

    # Markers for charts: since= ISO timestamp
    since = request.query_params.get('since')
    if since:
        try:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(since)
            if dt:
                qs = qs.filter(created_at__gte=dt)
        except Exception:
            pass

    open_base = AlertEvent.objects.filter(
        resolved_at__isnull=True, acknowledged_at__isnull=True
    ).exclude(event_type__in=HIGHLIGHT_TYPES).exclude(event_type__startswith='user_')
    total_open = open_base.filter(
        Q(severity__in=(AlertEvent.SEVERITY_WARN, AlertEvent.SEVERITY_CRITICAL))
        | Q(event_type__in=PROBLEM_TYPES)
    ).count()
    critical_open = AlertEvent.objects.filter(
        resolved_at__isnull=True,
        acknowledged_at__isnull=True,
        severity=AlertEvent.SEVERITY_CRITICAL,
    ).exclude(event_type__in=HIGHLIGHT_TYPES).count()

    events = list(qs[:limit])
    return Response({
        'results': AlertEventSerializer(events, many=True).data,
        'open_count': total_open,
        'critical_open_count': critical_open,
        'kind': kind,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activity_event_acknowledge(request, pk):
    try:
        event = AlertEvent.objects.get(pk=pk)
    except AlertEvent.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    event.acknowledged_at = timezone.now()
    event.save(update_fields=['acknowledged_at'])
    return Response(AlertEventSerializer(event).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activity_event_snooze(request, pk):
    try:
        event = AlertEvent.objects.get(pk=pk)
    except AlertEvent.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        minutes = int((request.data or {}).get('minutes', 60))
    except (TypeError, ValueError):
        minutes = 60
    minutes = max(5, min(24 * 60, minutes))
    event.muted_until = timezone.now() + timedelta(minutes=minutes)
    event.save(update_fields=['muted_until'])
    return Response(AlertEventSerializer(event).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activity_event_resolve(request, pk):
    try:
        event = AlertEvent.objects.get(pk=pk)
    except AlertEvent.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    event.resolved_at = timezone.now()
    event.save(update_fields=['resolved_at'])
    return Response(AlertEventSerializer(event).data)


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

