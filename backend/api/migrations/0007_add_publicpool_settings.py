# Generated migration for PublicPool support in CollectorSettings model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_add_collector_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectorsettings',
            name='pool_type',
            field=models.CharField(
                choices=[('ckpool', 'CKPool'), ('publicpool', 'Public Pool')],
                default='ckpool',
                help_text='Select which mining pool to use for statistics',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='publicpool_address',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Bitcoin address for PublicPool statistics',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='publicpool_url',
            field=models.CharField(
                blank=True,
                default='http://localhost:3334',
                help_text='PublicPool API URL (e.g., http://localhost:3334 or https://web.public-pool.io)',
                max_length=255,
            ),
        ),
    ]
