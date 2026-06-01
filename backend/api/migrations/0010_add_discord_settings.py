# Generated migration for adding Discord webhook notification settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_add_cost_analysis_settings'),
    ]

    operations = [
        # Add discord_enabled field
        migrations.AddField(
            model_name='collectorsettings',
            name='discord_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Enable Discord webhook notifications for device alerts'
            ),
        ),
        # Add discord_webhook_url field
        migrations.AddField(
            model_name='collectorsettings',
            name='discord_webhook_url',
            field=models.CharField(
                max_length=500,
                blank=True,
                default='',
                help_text='Discord webhook URL for alerts (create in Discord channel settings)'
            ),
        ),
    ]
