# Generated migration for adding cost analysis settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_add_best_session_difficulty'),
    ]

    operations = [
        # Add energy rate field
        migrations.AddField(
            model_name='collectorsettings',
            name='energy_rate',
            field=models.DecimalField(
                max_digits=10,
                decimal_places=4,
                default=0.12,
                help_text='Energy cost per kWh in selected currency'
            ),
        ),
        # Add energy currency field
        migrations.AddField(
            model_name='collectorsettings',
            name='energy_currency',
            field=models.CharField(
                max_length=3,
                choices=[
                    ('USD', 'US Dollar ($)'),
                    ('EUR', 'Euro (€)'),
                    ('GBP', 'British Pound (£)'),
                    ('CHF', 'Swiss Franc (CHF)'),
                ],
                default='USD',
                help_text='Currency for energy costs'
            ),
        ),
        # Add show revenue stats toggle
        migrations.AddField(
            model_name='collectorsettings',
            name='show_revenue_stats',
            field=models.BooleanField(
                default=True,
                help_text='Show mining revenue statistics (based on solo mining probability)'
            ),
        ),
        # Add cached BTC price
        migrations.AddField(
            model_name='collectorsettings',
            name='cached_btc_price',
            field=models.DecimalField(
                max_digits=20,
                decimal_places=2,
                default=100000,
                help_text='Cached Bitcoin price in USD'
            ),
        ),
        # Add cached network hashrate
        migrations.AddField(
            model_name='collectorsettings',
            name='cached_network_hashrate',
            field=models.DecimalField(
                max_digits=20,
                decimal_places=2,
                default=750,
                help_text='Cached network hashrate in EH/s'
            ),
        ),
        # Add cached network difficulty
        migrations.AddField(
            model_name='collectorsettings',
            name='cached_network_difficulty',
            field=models.DecimalField(
                max_digits=30,
                decimal_places=0,
                default=0,
                help_text='Cached network difficulty'
            ),
        ),
        # Add network data updated timestamp
        migrations.AddField(
            model_name='collectorsettings',
            name='network_data_updated_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When network data was last updated'
            ),
        ),
    ]
