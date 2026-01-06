# Generated migration for adding best_session_difficulty field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_add_publicpool_settings'),
    ]

    operations = [
        # Add best_session_difficulty column
        migrations.AddField(
            model_name='bitaxeminingstats',
            name='best_session_difficulty',
            field=models.BigIntegerField(
                blank=True,
                null=True,
                help_text="Current session best difficulty (from API 'bestSessionDiff')"
            ),
        ),
        # Update help_text for existing best_difficulty field
        migrations.AlterField(
            model_name='bitaxeminingstats',
            name='best_difficulty',
            field=models.BigIntegerField(
                blank=True,
                null=True,
                help_text="All-time best difficulty"
            ),
        ),
    ]
