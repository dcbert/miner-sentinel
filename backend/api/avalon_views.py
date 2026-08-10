"""
Avalon Nano 3s API views — registry dual-writes, stats read from unified tables.
"""

import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .avalon_serializers import AvalonDeviceSerializer
from .device_sync import delete_unified_device, sync_avalon_to_unified
from .models import AvalonDevice, Device, DeviceHardwareStats, DeviceMiningStats, DeviceSystemInfo
from .unified_serializers import (
    UnifiedDeviceAsAvalonSerializer,
    UnifiedHardwareSerializer,
    UnifiedMiningAsAvalonSerializer,
    UnifiedSystemAsAvalonSerializer,
)
from .views import _parse_int_param

logger = logging.getLogger(__name__)

_MAX_HOURS = 24 * 90


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_dashboard_stats(request):
    """Get Avalon dashboard statistics from unified tables."""
    try:
        devices = Device.objects.filter(make=Device.MAKE_AVALON)
        total_devices = devices.count()
        online_devices = devices.filter(is_active=True).count()
        offline_devices = total_devices - online_devices

        latest_stats = []
        latest_hardware = []
        for device in devices:
            latest_mining = DeviceMiningStats.objects.filter(device=device).first()
            latest_hw = DeviceHardwareStats.objects.filter(device=device).first()
            if latest_mining:
                latest_stats.append(latest_mining)
            if latest_hw:
                latest_hardware.append(latest_hw)

        total_hashrate = sum(stat.hashrate_ghs or 0 for stat in latest_stats)
        avg_temperature = (
            sum(hw.temperature_c or 0 for hw in latest_hardware) / len(latest_hardware)
            if latest_hardware else 0
        )
        total_power = sum(hw.power_watts or 0 for hw in latest_hardware)
        avg_efficiency = (
            sum(hw.efficiency_j_per_th or 0 for hw in latest_hardware) / len(latest_hardware)
            if latest_hardware else 0
        )
        total_accepted = sum(stat.shares_accepted or 0 for stat in latest_stats)
        total_rejected = sum(stat.shares_rejected or 0 for stat in latest_stats)

        device_payloads = []
        for device in devices:
            device_payloads.append({
                **UnifiedDeviceAsAvalonSerializer(device).data,
                'latest_mining_stats': (
                    UnifiedMiningAsAvalonSerializer(
                        DeviceMiningStats.objects.filter(device=device).first()
                    ).data
                    if DeviceMiningStats.objects.filter(device=device).exists() else None
                ),
                'latest_hardware_logs': (
                    UnifiedHardwareSerializer(
                        DeviceHardwareStats.objects.filter(device=device).first()
                    ).data
                    if DeviceHardwareStats.objects.filter(device=device).exists() else None
                ),
                'latest_system_info': (
                    UnifiedSystemAsAvalonSerializer(
                        DeviceSystemInfo.objects.filter(device=device).first()
                    ).data
                    if DeviceSystemInfo.objects.filter(device=device).exists() else None
                ),
            })

        return Response({
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': offline_devices,
            'total_hashrate_ghs': total_hashrate,
            'average_temperature': avg_temperature,
            'total_power_watts': total_power,
            'average_efficiency': avg_efficiency,
            'total_shares_accepted': total_accepted,
            'total_shares_rejected': total_rejected,
            'devices': device_payloads,
        })
    except Exception as e:
        logger.error(f"Error getting Avalon dashboard stats: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get dashboard statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def avalon_devices(request):
    """GET list / POST create Avalon devices (legacy + unified registry)."""
    try:
        if request.method == 'GET':
            # Prefer unified registry
            devices = Device.objects.filter(make=Device.MAKE_AVALON).order_by('device_id')
            if devices.exists():
                return Response(UnifiedDeviceAsAvalonSerializer(devices, many=True).data)
            legacy = AvalonDevice.objects.all().order_by('device_id')
            return Response(AvalonDeviceSerializer(legacy, many=True).data)

        elif request.method == 'POST':
            serializer = AvalonDeviceSerializer(data=request.data)
            if serializer.is_valid():
                instance = serializer.save()
                sync_avalon_to_unified(instance)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error with Avalon devices: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to process device request'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def avalon_device_detail(request, device_id):
    """GET / PUT / DELETE a single Avalon device."""
    try:
        unified = Device.objects.filter(make=Device.MAKE_AVALON, device_id=device_id).first()
        try:
            legacy = AvalonDevice.objects.get(device_id=device_id)
        except AvalonDevice.DoesNotExist:
            try:
                legacy = AvalonDevice.objects.get(pk=int(device_id))
            except (AvalonDevice.DoesNotExist, ValueError):
                legacy = None

        if request.method == 'GET':
            if unified:
                payload = UnifiedDeviceAsAvalonSerializer(unified).data
                payload['latest_mining_stats'] = None
                payload['latest_hardware_logs'] = None
                payload['latest_system_info'] = None
                m = DeviceMiningStats.objects.filter(device=unified).first()
                h = DeviceHardwareStats.objects.filter(device=unified).first()
                s = DeviceSystemInfo.objects.filter(device=unified).first()
                if m:
                    payload['latest_mining_stats'] = UnifiedMiningAsAvalonSerializer(m).data
                if h:
                    payload['latest_hardware_logs'] = UnifiedHardwareSerializer(h).data
                if s:
                    payload['latest_system_info'] = UnifiedSystemAsAvalonSerializer(s).data
                return Response(payload)
            if legacy:
                return Response(AvalonDeviceSerializer(legacy).data)
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        if not legacy:
            return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'PUT':
            serializer = AvalonDeviceSerializer(legacy, data=request.data, partial=True)
            if serializer.is_valid():
                instance = serializer.save()
                sync_avalon_to_unified(instance)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            device_id_value = legacy.device_id
            legacy.delete()
            delete_unified_device(Device.MAKE_AVALON, device_id_value)
            return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Error with Avalon device detail: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to process device request'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_mining_stats(request):
    """Mining statistics for Avalon devices from unified tables."""
    try:
        device_id = request.GET.get('device_id')
        hours = _parse_int_param(request.GET.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        limit = _parse_int_param(request.GET.get('limit', 100), 100, min_value=1, max_value=5000)
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)

        query = DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_AVALON,
            recorded_at__gte=start_time,
            recorded_at__lte=end_time,
        ).select_related('device')
        if device_id:
            query = query.filter(device__device_id=device_id)
        stats = query.order_by('-recorded_at')[:limit]
        return Response(UnifiedMiningAsAvalonSerializer(stats, many=True).data)
    except Exception as e:
        logger.error(f"Error getting Avalon mining stats: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get mining statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_hardware_logs(request):
    """Hardware logs for Avalon devices from unified tables."""
    try:
        device_id = request.GET.get('device_id')
        hours = _parse_int_param(request.GET.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        limit = _parse_int_param(request.GET.get('limit', 100), 100, min_value=1, max_value=5000)
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)

        query = DeviceHardwareStats.objects.filter(
            device__make=Device.MAKE_AVALON,
            recorded_at__gte=start_time,
            recorded_at__lte=end_time,
        ).select_related('device')
        if device_id:
            query = query.filter(device__device_id=device_id)
        logs = query.order_by('-recorded_at')[:limit]
        return Response(UnifiedHardwareSerializer(logs, many=True).data)
    except Exception as e:
        logger.error(f"Error getting Avalon hardware logs: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get hardware logs'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_hashrate_trends(request):
    """Hashrate trend points for Avalon devices."""
    try:
        device_id = request.GET.get('device_id')
        hours = _parse_int_param(request.GET.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        start_time = timezone.now() - timedelta(hours=hours)
        query = DeviceMiningStats.objects.filter(
            device__make=Device.MAKE_AVALON,
            recorded_at__gte=start_time,
        )
        if device_id:
            query = query.filter(device__device_id=device_id)
        stats = query.order_by('recorded_at').values(
            'recorded_at', 'hashrate_ghs', 'shares_accepted', 'shares_rejected', 'device__name'
        )
        return Response([
            {
                'recorded_at': row['recorded_at'],
                'hashrate_ghs': row['hashrate_ghs'],
                'shares_accepted': row['shares_accepted'],
                'shares_rejected': row['shares_rejected'],
                'device_name': row['device__name'],
            }
            for row in stats
        ])
    except Exception as e:
        logger.error(f"Error getting Avalon hashrate trends: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get hashrate trends'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_temperature_trends(request):
    """Temperature / power trends for Avalon devices."""
    try:
        device_id = request.GET.get('device_id')
        hours = _parse_int_param(request.GET.get('hours', 24), 24, min_value=1, max_value=_MAX_HOURS)
        start_time = timezone.now() - timedelta(hours=hours)
        query = DeviceHardwareStats.objects.filter(
            device__make=Device.MAKE_AVALON,
            recorded_at__gte=start_time,
        )
        if device_id:
            query = query.filter(device__device_id=device_id)
        logs = query.order_by('recorded_at').values(
            'recorded_at', 'temperature_c', 'power_watts', 'fan_speed_rpm', 'device__name'
        )
        return Response([
            {
                'recorded_at': row['recorded_at'],
                'temperature_c': row['temperature_c'],
                'power_watts': row['power_watts'],
                'fan_speed_rpm': row['fan_speed_rpm'],
                'device_name': row['device__name'],
            }
            for row in logs
        ])
    except Exception as e:
        logger.error(f"Error getting Avalon temperature trends: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get temperature trends'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def avalon_restart_device(request, device_id):
    """Restart a specific Avalon device via cgminer socket API."""
    import socket

    try:
        device = Device.objects.filter(make=Device.MAKE_AVALON, device_id=device_id).first()
        if device:
            name, ip = device.name, str(device.ip_address)
        else:
            try:
                legacy = AvalonDevice.objects.get(device_id=device_id)
            except AvalonDevice.DoesNotExist:
                return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)
            name, ip = legacy.device_name, str(legacy.ip_address)

        def send_restart_command(ip_addr):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((ip_addr, 4028))
                sock.send(b"ascset|0,reboot,0")
                response = sock.recv(1024)
                sock.close()
                return b'STATUS=S' in response
            except Exception as e:
                logger.error(f"Error sending restart command: {e}")
                return False

        success = send_restart_command(ip)
        if success:
            return Response({'message': f'Restart command sent to {name}'})
        return Response(
            {'error': 'Failed to send restart command'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Error restarting Avalon device: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to restart device'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
