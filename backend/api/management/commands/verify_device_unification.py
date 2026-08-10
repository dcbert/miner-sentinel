"""
Verify unified device/pool tables after migration.

Post Release C (legacy tables dropped): reports unified counts only.
Pre Release C: can compare legacy vs unified counts.

Usage:
  python manage.py verify_device_unification
  python manage.py verify_device_unification --strict
  python manage.py verify_device_unification --registry-only
"""
from django.core.management.base import BaseCommand, CommandError

from api.migration_utils import verify_unification_counts
from api.models import Device


class Command(BaseCommand):
    help = 'Verify unified device/pool tables (and legacy counts if still present)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with code 1 if any count mismatches (legacy era only)',
        )
        parser.add_argument(
            '--registry-only',
            action='store_true',
            help='Only report device registry count',
        )

    def handle(self, *args, **options):
        if options['registry_only']:
            unified = Device.objects.count()
            self.stdout.write(f'devices: unified={unified}')
            self.stdout.write(self.style.SUCCESS('Registry report complete.'))
            return

        result = verify_unification_counts()
        if not result.get('legacy_available', True):
            self.stdout.write('Release C: legacy tables not present.')
            for name, count in result.get('unified', {}).items():
                self.stdout.write(f'  {name}: unified={count}')
            self.stdout.write(self.style.SUCCESS(result.get('message', 'OK')))
            return

        self.stdout.write('Unification verification (legacy vs unified):')
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
