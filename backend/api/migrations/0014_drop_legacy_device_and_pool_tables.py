"""
Release C: drop legacy per-vendor tables after unified schema is sole writer/reader.

Prerequisite: 0011–0012 applied; collectors and API on unified tables only.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_notification_rules'),
    ]

    operations = [
        # Time-series / pool first (FK to device registries)
        migrations.DeleteModel(name='BitAxeMiningStats'),
        migrations.DeleteModel(name='BitAxeHardwareLog'),
        migrations.DeleteModel(name='BitAxeSystemInfo'),
        migrations.DeleteModel(name='BitAxePoolStats'),
        migrations.DeleteModel(name='AvalonMiningStats'),
        migrations.DeleteModel(name='AvalonHardwareLogs'),
        migrations.DeleteModel(name='AvalonSystemInfo'),
        # Registries last
        migrations.DeleteModel(name='BitAxeDevice'),
        migrations.DeleteModel(name='AvalonDevice'),
    ]
