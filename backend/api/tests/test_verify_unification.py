"""Tests for verify_device_unification management command (Release C)."""
from io import StringIO

import pytest
from django.core.management import call_command

from api.models import Device


@pytest.mark.django_db
def test_verify_device_unification_ok():
    """Release C: unified-only report succeeds."""
    Device.objects.create(
        device_id='bx-1',
        name='BX',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='10.0.0.1',
        is_active=True,
    )
    out = StringIO()
    call_command('verify_device_unification', stdout=out)
    text = out.getvalue().lower()
    assert 'release c' in text or 'unified' in text
    assert 'ok' in text or 'complete' in text or 'not present' in text


@pytest.mark.django_db
def test_verify_device_unification_registry_only():
    Device.objects.create(
        device_id='bx-1',
        name='BX',
        make=Device.MAKE_BITAXE,
        protocol=Device.PROTOCOL_HTTP_AXEOS,
        ip_address='10.0.0.1',
        is_active=True,
    )
    out = StringIO()
    call_command('verify_device_unification', '--registry-only', stdout=out)
    assert 'unified=1' in out.getvalue()


@pytest.mark.django_db
def test_verify_empty_registry():
    out = StringIO()
    call_command('verify_device_unification', '--registry-only', stdout=out)
    assert 'unified=0' in out.getvalue()
