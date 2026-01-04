# Generated migration for CollectorSettings model
# This migration creates the table and populates it with initial data from environment variables

import os

import django.utils.timezone
from django.db import migrations, models


def populate_initial_settings(apps, schema_editor):
    """
    Populate the CollectorSettings table with values from environment variables.
    This runs once during the initial migration.
    """
    CollectorSettings = apps.get_model('api', 'CollectorSettings')

    # Read from environment variables with defaults
    settings = CollectorSettings(
        id=1,
        polling_interval_minutes=int(os.environ.get('POLLING_INTERVAL_MINUTES', 15)),
        device_check_interval_minutes=int(os.environ.get('DEVICE_CHECK_INTERVAL_MINUTES', 5)),
        ckpool_address=os.environ.get('CKPOOL_ADDRESS', ''),
        ckpool_url=os.environ.get('CKPOOL_URL', 'https://eusolo.ckpool.org'),
        telegram_enabled=os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true',
        telegram_bot_token=os.environ.get('TELEGRAM_BOT_TOKEN', ''),
        telegram_chat_id=os.environ.get('TELEGRAM_CHAT_ID', ''),
    )
    settings.save()


def reverse_populate(apps, schema_editor):
    """Reverse migration - delete settings."""
    CollectorSettings = apps.get_model('api', 'CollectorSettings')
    CollectorSettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_add_avalon_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectorSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('polling_interval_minutes', models.IntegerField(default=15, help_text='How often to poll devices for data (in minutes)')),
                ('device_check_interval_minutes', models.IntegerField(default=5, help_text='How often to check for new/updated devices (in minutes)')),
                ('ckpool_address', models.CharField(blank=True, default='', help_text='Bitcoin address for CKPool statistics', max_length=255)),
                ('ckpool_url', models.CharField(default='https://eusolo.ckpool.org', help_text='CKPool server URL', max_length=255)),
                ('telegram_enabled', models.BooleanField(default=False)),
                ('telegram_bot_token', models.CharField(blank=True, default='', max_length=255)),
                ('telegram_chat_id', models.CharField(blank=True, default='', max_length=255)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name': 'Collector Settings',
                'verbose_name_plural': 'Collector Settings',
                'db_table': 'collector_settings',
            },
        ),
        migrations.RunSQL(
            'ALTER TABLE collector_settings ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;',
            ),
        migrations.RunPython(populate_initial_settings, reverse_populate),
    ]
