"""
Seed / upsert lab devices for API and control testing.

Lab IPs (local network only — do not commit secrets):
  Avalon   192.168.1.11  make=avalon  cgminer :4028
  NerdQAxe 192.168.1.12  make=bitaxe  AxeOS HTTP
  Bitaxe   192.168.1.7   make=bitaxe  AxeOS HTTP

Usage:
  python manage.py seed_lab_devices
  python manage.py seed_lab_devices --dry-run
"""

from django.core.management.base import BaseCommand

from api.models import Device
from api.serializers import MAKE_PROTOCOL

LAB_DEVICES = [
    {
        'device_id': 'avalon-mini-3s',
        'name': 'Avalon Mini 3s',
        'make': Device.MAKE_AVALON,
        'ip_address': '192.168.1.11',
        'port': 4028,
        'model': 'Nano3s',
    },
    {
        'device_id': 'nerdqaxe-plus-plus-1',
        'name': 'Nerdqaxe++ 1',
        'make': Device.MAKE_BITAXE,
        'ip_address': '192.168.1.12',
        'port': 80,
        'model': 'NerdQAxe++',
    },
    {
        'device_id': 'bitaxe-lab-7',
        'name': 'Bitaxe Lab',
        'make': Device.MAKE_BITAXE,
        'ip_address': '192.168.1.7',
        'port': 80,
        'model': 'Bitaxe',
    },
]


class Command(BaseCommand):
    help = 'Upsert lab devices for control/API testing (Avalon .11, NerdQAxe .12, Bitaxe .7)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without writing',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        created_n = updated_n = 0

        for spec in LAB_DEVICES:
            make = spec['make']
            protocol = MAKE_PROTOCOL.get(make, Device.PROTOCOL_CUSTOM)
            defaults = {
                'name': spec['name'],
                'protocol': protocol,
                'ip_address': spec['ip_address'],
                'port': spec['port'],
                'model': spec.get('model'),
                'is_active': True,
            }

            # Prefer match by make+ip so we do not duplicate if device_id differs
            existing = Device.objects.filter(make=make, ip_address=spec['ip_address']).first()
            if existing:
                action = 'update'
                if not dry:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    # Keep existing device_id if already set; only fill if empty
                    if not existing.device_id:
                        existing.device_id = spec['device_id']
                    existing.save()
                updated_n += 1
                self.stdout.write(
                    f"{action}: {make} {spec['ip_address']} "
                    f"({existing.device_id if existing else spec['device_id']})"
                )
                continue

            by_id = Device.objects.filter(make=make, device_id=spec['device_id']).first()
            if by_id:
                action = 'update'
                if not dry:
                    for key, value in defaults.items():
                        setattr(by_id, key, value)
                    by_id.save()
                updated_n += 1
                self.stdout.write(f'{action}: {make}:{spec["device_id"]} -> {spec["ip_address"]}')
                continue

            action = 'create'
            if not dry:
                Device.objects.create(
                    device_id=spec['device_id'],
                    make=make,
                    **defaults,
                )
            created_n += 1
            self.stdout.write(f'{action}: {make}:{spec["device_id"]} @ {spec["ip_address"]}')

        summary = f'Lab devices: created={created_n} updated={updated_n}'
        if dry:
            summary += ' (dry-run)'
        self.stdout.write(self.style.SUCCESS(summary))
