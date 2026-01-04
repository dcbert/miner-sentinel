# Generated manually for adding device status tracking fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_bitaxesysteminfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='bitaxedevice',
            name='last_seen_at',
            field=models.DateTimeField(blank=True, null=True, help_text='Last successful connection'),
        ),
        migrations.AddField(
            model_name='bitaxedevice',
            name='error_message',
            field=models.TextField(blank=True, null=True, help_text='Last error message if offline'),
        ),
    ]