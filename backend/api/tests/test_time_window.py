"""Tests for shared time-window query param parsing."""
from datetime import timedelta

import pytest
from django.utils import timezone

from api.time_window import MAX_HOURS, parse_int_param, parse_time_window


class TestParseIntParam:
    def test_valid(self):
        assert parse_int_param('24', 1) == 24
        assert parse_int_param(7, 1) == 7

    def test_invalid_falls_back(self):
        assert parse_int_param('abc', 24) == 24
        assert parse_int_param(None, 24) == 24

    def test_clamps(self):
        assert parse_int_param('0', 24, min_value=1) == 1
        assert parse_int_param('99999', 24, min_value=1, max_value=100) == 100


class TestParseTimeWindow:
    def test_default_hours(self):
        now = timezone.now()
        w = parse_time_window({}, now=now)
        assert w.hours == 24
        assert w.days == 1
        assert w.end == now
        assert abs((w.end - w.start) - timedelta(hours=24)) < timedelta(seconds=1)

    def test_hours_only_single_window(self):
        now = timezone.now()
        w = parse_time_window({'hours': '6'}, now=now)
        assert w.hours == 6
        assert w.days == 1  # ceil(6/24)
        assert abs((w.end - w.start) - timedelta(hours=6)) < timedelta(seconds=1)

    def test_one_hour_does_not_expand_to_24h_window(self):
        now = timezone.now()
        w = parse_time_window({'hours': '1', 'days': '1'}, now=now)
        # hours wins; window is 1h not 1 day
        assert w.hours == 1
        assert abs((w.end - w.start) - timedelta(hours=1)) < timedelta(seconds=1)

    def test_days_only(self):
        now = timezone.now()
        w = parse_time_window({'days': '7'}, now=now)
        assert w.hours == 168
        assert w.days == 7

    def test_absolute_from_to(self):
        # Single now() so the span is exactly 48h (no dual-clock microsecond skew)
        now = timezone.now()
        start = now - timedelta(days=3)
        end = now - timedelta(days=1)
        w = parse_time_window({
            'from': start.isoformat(),
            'to': end.isoformat(),
            'hours': '999',  # ignored when from/to valid
        })
        assert abs(w.start - start) < timedelta(seconds=1)
        assert abs(w.end - end) < timedelta(seconds=1)
        assert w.hours == 48
        assert w.days == 2

    def test_absolute_clamped_to_max(self):
        end = timezone.now()
        start = end - timedelta(days=200)
        w = parse_time_window({
            'from': start.isoformat(),
            'to': end.isoformat(),
        })
        assert w.hours == MAX_HOURS
        assert abs((w.end - w.start) - timedelta(hours=MAX_HOURS)) < timedelta(seconds=2)

    def test_invalid_from_to_falls_back_to_hours(self):
        now = timezone.now()
        w = parse_time_window({'from': 'nope', 'to': 'nope', 'hours': '12'}, now=now)
        assert w.hours == 12

    def test_clamps_huge_hours(self):
        w = parse_time_window({'hours': '999999'})
        assert w.hours == MAX_HOURS
        assert w.days == 90


@pytest.fixture
def auth_client(db):
    from django.contrib.auth.models import User
    from rest_framework.test import APIClient

    user = User.objects.create_user(username='tw', password='p')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestOverviewWindowApi:
    def test_overview_absolute_window_echoed(self, auth_client):
        end = timezone.now()
        start = end - timedelta(hours=6)
        resp = auth_client.get(
            '/api/overview/analytics/',
            {'from': start.isoformat(), 'to': end.isoformat()},
        )
        assert resp.status_code == 200
        assert resp.data['overview']['data_collection_period_hours'] == 6
        assert 'window_start' in resp.data['overview']
        assert 'window_end' in resp.data['overview']
