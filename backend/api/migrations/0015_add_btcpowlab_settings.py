from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_drop_legacy_device_and_pool_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectorsettings',
            name='btcpowlab_address',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Bitcoin address for BTC PoW Lab statistics',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='btcpowlab_url',
            field=models.CharField(
                blank=True,
                default='https://btcpowlab-pool.com/public/v1',
                help_text='BTC PoW Lab public API base URL',
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name='collectorsettings',
            name='pool_type',
            field=models.CharField(
                choices=[
                    ('ckpool', 'CKPool'),
                    ('publicpool', 'Public Pool'),
                    ('btcpowlab', 'BTC PoW Lab'),
                ],
                default='ckpool',
                help_text='Select which mining pool to use for statistics',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='poolstats',
            name='pool_type',
            field=models.CharField(
                choices=[
                    ('ckpool', 'CKPool'),
                    ('publicpool', 'Public Pool'),
                    ('btcpowlab', 'BTC PoW Lab'),
                    ('ocean', 'Ocean'),
                    ('other', 'Other'),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
    ]
