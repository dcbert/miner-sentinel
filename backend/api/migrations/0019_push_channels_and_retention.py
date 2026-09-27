# Generated manually for push channels + retention policy fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_awareness_alert_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectorsettings',
            name='ntfy_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Enable ntfy push notifications (topic URL)',
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='ntfy_url',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Full ntfy topic URL (e.g. https://ntfy.sh/mytopic or self-hosted)',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='ntfy_token',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Optional ntfy access token',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='gotify_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Enable Gotify push notifications',
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='gotify_url',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Gotify server base URL (e.g. https://gotify.example.com)',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='gotify_token',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Gotify application token',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='webhook_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Enable generic JSON webhook for alerts',
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='webhook_url',
            field=models.CharField(
                blank=True,
                default='',
                help_text='POST JSON alerts to this URL',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='metrics_retention_days',
            field=models.IntegerField(
                default=90,
                help_text='Days to keep device_*_stats and pool_stats (0 = forever)',
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='alert_retention_days',
            field=models.IntegerField(
                default=0,
                help_text='Days to keep resolved AlertEvents (0 = forever; open alerts never pruned)',
            ),
        ),
    ]
