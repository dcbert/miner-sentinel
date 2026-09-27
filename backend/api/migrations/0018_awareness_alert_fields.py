# Extend AlertEvent for awareness (mute/resolve/fingerprint) + quiet hours + faster poll default

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_add_alert_event'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collectorsettings',
            name='polling_interval_minutes',
            field=models.IntegerField(
                default=2,
                help_text='How often to poll devices for data (in minutes)',
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='quiet_hours_enabled',
            field=models.BooleanField(
                default=False,
                help_text='When enabled, info/warn alerts skip chat during quiet hours (critical still delivered)',
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='quiet_hours_start',
            field=models.CharField(
                default='22:00',
                help_text='Quiet hours start (HH:MM, local server time)',
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='quiet_hours_end',
            field=models.CharField(
                default='07:00',
                help_text='Quiet hours end (HH:MM, local server time)',
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='alert_repeat_minutes',
            field=models.IntegerField(
                default=60,
                help_text='Minutes before re-notifying the same open problem via chat',
            ),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='device_make',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='device_key',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Vendor device_id string',
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='device_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='fingerprint',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Dedup key: event_type + device identity',
                max_length=191,
            ),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='muted_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alertevent',
            name='last_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='alertevent',
            index=models.Index(fields=['fingerprint', '-created_at'], name='alert_event_fingerp_idx'),
        ),
        migrations.AddIndex(
            model_name='alertevent',
            index=models.Index(fields=['resolved_at', 'acknowledged_at'], name='alert_event_open_idx'),
        ),
        migrations.AddIndex(
            model_name='alertevent',
            index=models.Index(fields=['severity', '-created_at'], name='alert_event_sev_idx'),
        ),
    ]
