"""
Prune old device/pool metrics and optionally resolved alert events.

Respects CollectorSettings.metrics_retention_days and alert_retention_days
(0 = keep forever for that category). Open (unresolved) alerts are never deleted.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import (
    AlertEvent,
    CollectorSettings,
    DeviceHardwareStats,
    DeviceMiningStats,
    DeviceSystemInfo,
    PoolStats,
)


class Command(BaseCommand):
    help = 'Prune old metrics and resolved alerts per retention settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without deleting',
        )
        parser.add_argument(
            '--metrics-days',
            type=int,
            default=None,
            help='Override metrics_retention_days for this run',
        )
        parser.add_argument(
            '--alert-days',
            type=int,
            default=None,
            help='Override alert_retention_days for this run',
        )

    def handle(self, *args, **options):
        settings = CollectorSettings.get_settings()
        metrics_days = options['metrics_days']
        if metrics_days is None:
            metrics_days = int(settings.metrics_retention_days or 0)
        alert_days = options['alert_days']
        if alert_days is None:
            alert_days = int(settings.alert_retention_days or 0)
        dry = options['dry_run']
        now = timezone.now()
        deleted = {}

        if metrics_days > 0:
            cutoff = now - timedelta(days=metrics_days)
            for label, model in (
                ('mining', DeviceMiningStats),
                ('hardware', DeviceHardwareStats),
                ('system', DeviceSystemInfo),
                ('pool', PoolStats),
            ):
                qs = model.objects.filter(recorded_at__lt=cutoff)
                count = qs.count()
                deleted[label] = count
                if not dry and count:
                    qs.delete()
        else:
            self.stdout.write('metrics_retention_days=0 — skipping metrics prune')

        if alert_days > 0:
            alert_cutoff = now - timedelta(days=alert_days)
            qs = AlertEvent.objects.filter(
                created_at__lt=alert_cutoff,
                resolved_at__isnull=False,
            )
            count = qs.count()
            deleted['alerts'] = count
            if not dry and count:
                qs.delete()
        else:
            self.stdout.write('alert_retention_days=0 — keeping AlertEvents forever')
            deleted['alerts'] = 0

        mode = 'Would delete' if dry else 'Deleted'
        self.stdout.write(self.style.SUCCESS(f'{mode}: {deleted}'))
