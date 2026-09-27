from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_add_btcpowlab_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectorsettings',
            name='parasite_address',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Bitcoin address for Parasite Pool statistics',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='collectorsettings',
            name='parasite_url',
            field=models.CharField(
                blank=True,
                default='https://parasite.space/api',
                help_text='Parasite Pool public API base URL',
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
                    ('parasite', 'Parasite'),
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
                    ('parasite', 'Parasite'),
                    ('ocean', 'Ocean'),
                    ('other', 'Other'),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
    ]
