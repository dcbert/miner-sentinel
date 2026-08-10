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
    path('', include(router.urls)),
    path(
        'devices/<str:make>/<str:device_id>/details/',
        views.device_details_by_make_id,
        name='device-details-by-make-id',
    ),
    # Analytics endpoints
    path('overview/analytics/', views.overview_analytics, name='overview-analytics'),
    path('analytics/detailed/', views.detailed_analytics, name='detailed-analytics'),
    # Settings endpoints
    path('settings/collector/', views.collector_settings_view, name='collector-settings'),
    path('settings/collector/poll/', views.trigger_collector_poll, name='collector-poll'),
    path('settings/collector/test-telegram/', views.test_telegram_notification, name='test-telegram'),
    path('settings/collector/test-discord/', views.test_discord_notification, name='test-discord'),
    path('settings/network-data/', views.get_network_data, name='network-data'),
    path('settings/network-data/refresh/', views.refresh_network_data, name='refresh-network-data'),
    # Authentication endpoints
    path('auth/csrf/', views.csrf_token_view, name='csrf-token'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/user/', views.current_user_view, name='current-user'),
]
