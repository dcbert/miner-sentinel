from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import avalon_views, views

router = DefaultRouter()

# BitAxe endpoints
router.register(r'bitaxe/devices', views.BitAxeDeviceViewSet, basename='bitaxe-devices')
router.register(r'bitaxe/mining', views.BitAxeMiningStatsViewSet, basename='bitaxe-mining')
router.register(r'bitaxe/hardware', views.BitAxeHardwareLogViewSet, basename='bitaxe-hardware')
router.register(r'bitaxe/system', views.BitAxeSystemInfoViewSet, basename='bitaxe-system')
router.register(r'bitaxe/pool', views.BitAxePoolStatsViewSet, basename='bitaxe-pool')

urlpatterns = [
    path('', include(router.urls)),
    # Analytics endpoints
    path('overview/analytics/', views.overview_analytics, name='overview-analytics'),
    path('analytics/detailed/', views.detailed_analytics, name='detailed-analytics'),
    # Avalon endpoints
    path('avalon/dashboard/', avalon_views.avalon_dashboard_stats, name='avalon-dashboard'),
    path('avalon/devices/', avalon_views.avalon_devices, name='avalon-devices'),
    path('avalon/devices/<str:device_id>/', avalon_views.avalon_device_detail, name='avalon-device-detail'),
    path('avalon/mining-stats/', avalon_views.avalon_mining_stats, name='avalon-mining-stats'),
    path('avalon/hardware-logs/', avalon_views.avalon_hardware_logs, name='avalon-hardware-logs'),
    path('avalon/hashrate-trends/', avalon_views.avalon_hashrate_trends, name='avalon-hashrate-trends'),
    path('avalon/temperature-trends/', avalon_views.avalon_temperature_trends, name='avalon-temperature-trends'),
    path('avalon/devices/<str:device_id>/restart/', avalon_views.avalon_restart_device, name='avalon-restart-device'),
    # Settings endpoints
    path('settings/collector/', views.collector_settings_view, name='collector-settings'),
    path('settings/collector/poll/', views.trigger_collector_poll, name='collector-poll'),
    # Authentication endpoints
    path('auth/csrf/', views.csrf_token_view, name='csrf-token'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/user/', views.current_user_view, name='current-user'),
]
