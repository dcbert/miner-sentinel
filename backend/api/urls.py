from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

# Unified fleet endpoints
router.register(r'devices', views.DeviceViewSet, basename='devices')
router.register(r'mining', views.FleetMiningViewSet, basename='mining')
router.register(r'hardware', views.FleetHardwareViewSet, basename='hardware')
router.register(r'pool', views.PoolStatsViewSet, basename='pool')

urlpatterns = [
    # Explicit device routes before router so "discover" is not treated as a pk
    path('devices/discover/', views.discover_devices_view, name='devices-discover'),
    path(
        'devices/<str:make>/<str:device_id>/details/',
        views.device_details_by_make_id,
        name='device-details-by-make-id',
    ),
    path(
        'devices/<str:make>/<str:device_id>/control/',
        views.device_control,
        name='device-control',
    ),
    path(
        'devices/<str:make>/<str:device_id>/capabilities/',
        views.device_capabilities,
        name='device-capabilities',
    ),
    # Explicit pool routes before router so "stratum-compare" is not treated as a pk
    path('pool/stratum-compare/', views.stratum_pool_compare, name='stratum-pool-compare'),
    path('', include(router.urls)),
    path('advisor/', views.advisor_view, name='advisor'),
    path('export/inventory.csv', views.export_inventory_csv, name='export-inventory'),
    path('settings/push-channels/', views.push_channels_status, name='push-channels'),
    # Analytics endpoints
    path('overview/analytics/', views.overview_analytics, name='overview-analytics'),
    path('analytics/detailed/', views.detailed_analytics, name='detailed-analytics'),
    # Settings endpoints
    path('settings/collector/', views.collector_settings_view, name='collector-settings'),
    path('settings/collector/status/', views.collector_status_view, name='collector-status'),
    path('settings/collector/poll/', views.trigger_collector_poll, name='collector-poll'),
    path('settings/collector/test-telegram/', views.test_telegram_notification, name='test-telegram'),
    path('settings/collector/test-discord/', views.test_discord_notification, name='test-discord'),
    path('settings/collector/test-push/', views.test_push_notification, name='test-push'),
    path('settings/network-data/', views.get_network_data, name='network-data'),
    path('settings/network-data/refresh/', views.refresh_network_data, name='refresh-network-data'),
    # Activity / alerts
    path('activity/', views.activity_events_list, name='activity-list'),
    path('activity/<int:pk>/acknowledge/', views.activity_event_acknowledge, name='activity-ack'),
    path('activity/<int:pk>/snooze/', views.activity_event_snooze, name='activity-snooze'),
    path('activity/<int:pk>/resolve/', views.activity_event_resolve, name='activity-resolve'),
    # Authentication endpoints
    path('auth/csrf/', views.csrf_token_view, name='csrf-token'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/user/', views.current_user_view, name='current-user'),
]
