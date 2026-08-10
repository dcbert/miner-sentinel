# Notification rules JSON for per-event alert toggles and thresholds

from django.db import migrations, models


def seed_notification_rules(apps, schema_editor):
    CollectorSettings = apps.get_model('api', 'CollectorSettings')
    defaults = {
        'device_offline': {'enabled': True},
        'device_online': {'enabled': True},
        'hashrate_stagnation': {
            'enabled': True,
            'threshold_collections': 3,
            'tolerance_ghs': 0.1,
        },
        'auto_restart': {'enabled': True},
        'best_difficulty': {
            'enabled': True,
            'min_improvement_percent': 5.0,
        },
    }
    for row in CollectorSettings.objects.all():
        if not row.notification_rules:
            row.notification_rules = defaults
            row.save(update_fields=['notification_rules'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_migrate_legacy_device_and_pool_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectorsettings',
            name='notification_rules',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Alert type toggles and tuning (offline, online, stagnation, restart, best difficulty)',
            ),
        ),
        migrations.RunPython(seed_notification_rules, migrations.RunPython.noop),
    ]
