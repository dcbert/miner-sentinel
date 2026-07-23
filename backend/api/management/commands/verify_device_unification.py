"""
Verify legacy tables and unified tables have matching row counts.

Intended to run immediately after migration 0012 (data backfill).
After Release B single-write, new samples land only in unified tables, so
time-series counts may diverge from legacy — that is expected.

Usage:
  python manage.py verify_device_unification
  python manage.py verify_device_unification --strict  # exit 1 on mismatch
  python manage.py verify_device_unification --registry-only  # devices only
"""
from django.core.management.base import BaseCommand, CommandError

from api.migration_utils import verify_unification_counts
from api.models import AvalonDevice, BitAxeDevice, Device


class Command(BaseCommand):
    help = 'Verify unified device/pool tables match legacy table counts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with code 1 if any count mismatches',
        )
        parser.add_argument(
            '--registry-only',
            action='store_true',
            help='Only compare device registry counts (ignores time-series after single-write)',
        )

    def handle(self, *args, **options):
        if options['registry_only']:
            legacy = BitAxeDevice.objects.count() + AvalonDevice.objects.count()
            unified = Device.objects.count()
            self.stdout.write(f'devices: legacy={legacy} unified={unified}')
            if legacy == unified:
                self.stdout.write(self.style.SUCCESS('Registry counts match.'))
            else:
                msg = 'Device registry count mismatch.'
                if options['strict']:
                    raise CommandError(msg)
                self.stdout.write(self.style.WARNING(msg))
            return

        result = verify_unification_counts()
        self.stdout.write('Unification verification (post-migration snapshot):')
        for name, (legacy, unified) in result['checks'].items():
            status = 'OK' if legacy == unified else 'MISMATCH'
            self.stdout.write(f'  {name}: legacy={legacy} unified={unified} [{status}]')

        if result['ok']:
            self.stdout.write(self.style.SUCCESS('All counts match.'))
        else:
            msg = (
                'Count mismatch between legacy and unified tables. '
                'Expected only right after 0012; after single-write, use --registry-only.'
            )
            if options['strict']:
                raise CommandError(msg)
            self.stdout.write(self.style.WARNING(msg))
