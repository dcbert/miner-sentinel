"""
Copy legacy bitaxe_*/avalon_* tables into unified devices / pool_stats tables.

Zero data loss: only reads legacy tables and inserts into new tables.
Idempotent via migration_utils.migrate_legacy_to_unified.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    from api.migration_utils import migrate_legacy_to_unified
    migrate_legacy_to_unified(apps, schema_editor)


def backwards(apps, schema_editor):
    from api.migration_utils import reverse_unified_data
    reverse_unified_data(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_unified_device_and_pool_schema'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
