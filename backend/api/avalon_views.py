"""
Avalon Nano 3s API views for Django REST Framework
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
from django.db.models import Avg, Count, Max, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .avalon_serializers import (
    AvalonDashboardStatsSerializer,
    AvalonDeviceDetailSerializer,
    AvalonDeviceSerializer,
    AvalonHardwareLogsSerializer,
    AvalonMiningStatsSerializer,
    AvalonSystemInfoSerializer,
)
from .models import AvalonDevice, AvalonHardwareLogs, AvalonMiningStats, AvalonSystemInfo

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_dashboard_stats(request):
    """
    Get Avalon dashboard statistics including device status and aggregated metrics.
    """
    try:
        # Get all devices with their latest data
        devices = AvalonDevice.objects.all()

        # Count devices by status
        total_devices = devices.count()
        online_devices = devices.filter(is_active=True).count()
        offline_devices = total_devices - online_devices

        # Get latest mining stats for aggregation
        latest_stats = []
        latest_hardware = []

        for device in devices:
            latest_mining = device.mining_stats.first()
            latest_hw = device.hardware_logs.first()

            if latest_mining:
                latest_stats.append(latest_mining)
            if latest_hw:
                latest_hardware.append(latest_hw)

        # Calculate aggregated metrics
        total_hashrate = sum(stat.hashrate_ghs for stat in latest_stats)
        avg_temperature = sum(hw.temperature_c for hw in latest_hardware) / len(latest_hardware) if latest_hardware else 0
        total_power = sum(hw.power_watts for hw in latest_hardware)
        avg_efficiency = sum(hw.efficiency_j_per_th for hw in latest_hardware) / len(latest_hardware) if latest_hardware else 0
        total_accepted = sum(stat.shares_accepted for stat in latest_stats)
        total_rejected = sum(stat.shares_rejected for stat in latest_stats)

        # Prepare response data
        dashboard_data = {
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': offline_devices,
            'total_hashrate_ghs': total_hashrate,
            'average_temperature': avg_temperature,
            'total_power_watts': total_power,
            'average_efficiency': avg_efficiency,
            'total_shares_accepted': total_accepted,
            'total_shares_rejected': total_rejected,
            'devices': devices
        }

        serializer = AvalonDashboardStatsSerializer(dashboard_data)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error getting Avalon dashboard stats: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get dashboard statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def avalon_devices(request):
    """
    GET: Get list of all Avalon devices.
    POST: Create a new Avalon device.
    """
    try:
        if request.method == 'GET':
            devices = AvalonDevice.objects.all().order_by('device_id')
            serializer = AvalonDeviceSerializer(devices, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = AvalonDeviceSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error with Avalon devices: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to process device request'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def avalon_device_detail(request, device_id):
    """
    GET: Get detailed information for a specific Avalon device.
    PUT: Update an Avalon device.
    DELETE: Delete an Avalon device.
    """
    try:
        # Try to find by device_id first, then by pk (id)
        try:
            device = AvalonDevice.objects.get(device_id=device_id)
        except AvalonDevice.DoesNotExist:
            try:
                device = AvalonDevice.objects.get(pk=int(device_id))
            except (AvalonDevice.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Device not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        if request.method == 'GET':
            serializer = AvalonDeviceDetailSerializer(device)
            return Response(serializer.data)

        elif request.method == 'PUT':
            serializer = AvalonDeviceSerializer(device, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            device.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Error with Avalon device detail: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to process device request'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_mining_stats(request):
    """
    Get mining statistics for all Avalon devices.

    Query parameters:
    - device_id: Filter by specific device
    - hours: Number of hours to look back (default: 24)
    - limit: Maximum number of records (default: 100)
    """
    try:
        device_id = request.GET.get('device_id')
        hours = int(request.GET.get('hours', 24))
        limit = int(request.GET.get('limit', 100))

        # Calculate time range
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)

        # Build query
        query = AvalonMiningStats.objects.filter(
            recorded_at__gte=start_time,
            recorded_at__lte=end_time
        )

        if device_id:
            query = query.filter(device__device_id=device_id)

        stats = query.order_by('-recorded_at')[:limit]
        serializer = AvalonMiningStatsSerializer(stats, many=True)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error getting Avalon mining stats: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get mining statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_hardware_logs(request):
    """
    Get hardware monitoring logs for all Avalon devices.

    Query parameters:
    - device_id: Filter by specific device
    - hours: Number of hours to look back (default: 24)
    - limit: Maximum number of records (default: 100)
    """
    try:
        device_id = request.GET.get('device_id')
        hours = int(request.GET.get('hours', 24))
        limit = int(request.GET.get('limit', 100))

        # Calculate time range
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)

        # Build query
        query = AvalonHardwareLogs.objects.filter(
            recorded_at__gte=start_time,
            recorded_at__lte=end_time
        )

        if device_id:
            query = query.filter(device__device_id=device_id)

        logs = query.order_by('-recorded_at')[:limit]
        serializer = AvalonHardwareLogsSerializer(logs, many=True)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error getting Avalon hardware logs: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get hardware logs'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_hashrate_trends(request):
    """
    Get hashrate trends for Avalon devices over time.

    Query parameters:
    - device_id: Filter by specific device
    - hours: Number of hours to look back (default: 24)
    - interval: Grouping interval in minutes (default: 60)
    """
    try:
        device_id = request.GET.get('device_id')
        hours = int(request.GET.get('hours', 24))
        interval = int(request.GET.get('interval', 60))

        # Calculate time range
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)

        # Build query
        query = AvalonMiningStats.objects.filter(
            recorded_at__gte=start_time,
            recorded_at__lte=end_time
        )

        if device_id:
            query = query.filter(device__device_id=device_id)

        # Get data and convert to DataFrame for easier processing
        stats = query.order_by('recorded_at').values(
            'recorded_at', 'hashrate_ghs', 'device__device_id', 'device__device_name'
        )

        if not stats:
            return Response([])

        df = pd.DataFrame(stats)
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])

        # Group by time intervals
        df.set_index('recorded_at', inplace=True)
        grouped = df.groupby([
            pd.Grouper(freq=f'{interval}min'),
            'device__device_id'
        ]).agg({
            'hashrate_ghs': 'mean',
            'device__device_name': 'first'
        }).reset_index()

        # Format response
        trends = []
        for _, row in grouped.iterrows():
            trends.append({
                'timestamp': row['recorded_at'].isoformat(),
                'device_id': row['device__device_id'],
                'device_name': row['device__device_name'],
                'hashrate_ghs': round(row['hashrate_ghs'], 2)
            })

        return Response(trends)

    except Exception as e:
        logger.error(f"Error getting Avalon hashrate trends: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get hashrate trends'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def avalon_temperature_trends(request):
    """
    Get temperature trends for Avalon devices over time.
    """
    try:
        device_id = request.GET.get('device_id')
        hours = int(request.GET.get('hours', 24))
        interval = int(request.GET.get('interval', 60))

        # Calculate time range
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)

        # Build query
        query = AvalonHardwareLogs.objects.filter(
            recorded_at__gte=start_time,
            recorded_at__lte=end_time
        )

        if device_id:
            query = query.filter(device__device_id=device_id)

        # Get data and convert to DataFrame
        logs = query.order_by('recorded_at').values(
            'recorded_at', 'temperature_c', 'power_watts',
            'device__device_id', 'device__device_name'
        )

        if not logs:
            return Response([])

        df = pd.DataFrame(logs)
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])

        # Group by time intervals
        df.set_index('recorded_at', inplace=True)
        grouped = df.groupby([
            pd.Grouper(freq=f'{interval}min'),
            'device__device_id'
        ]).agg({
            'temperature_c': 'mean',
            'power_watts': 'mean',
            'device__device_name': 'first'
        }).reset_index()

        # Format response
        trends = []
        for _, row in grouped.iterrows():
            trends.append({
                'timestamp': row['recorded_at'].isoformat(),
                'device_id': row['device__device_id'],
                'device_name': row['device__device_name'],
                'temperature_c': round(row['temperature_c'], 1),
                'power_watts': round(row['power_watts'], 1)
            })

        return Response(trends)

    except Exception as e:
        logger.error(f"Error getting Avalon temperature trends: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to get temperature trends'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def avalon_restart_device(request, device_id):
    """
    Restart a specific Avalon device.
    """
    try:
        device = AvalonDevice.objects.get(device_id=device_id)

        # Import socket for direct communication
        import socket

        def send_restart_command(ip):
            """Send restart command via socket."""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((ip, 4028))
                sock.send(b"ascset|0,reboot,0")
                response = sock.recv(1024)
                sock.close()
                return b'STATUS=S' in response
            except Exception as e:
                logger.error(f"Error sending restart command: {e}")
                return False

        success = send_restart_command(device.ip_address)

        if success:
            return Response({'message': f'Restart command sent to {device.device_name}'})
        else:
            return Response(
                {'error': 'Failed to send restart command'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except AvalonDevice.DoesNotExist:
        return Response(
            {'error': 'Device not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error restarting Avalon device: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to restart device'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )