# Generated manually on 2026-03-23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mywifipass', '0011_migrate_wifiuser_networks_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wifiuser',
            name='wifiLocation',
        ),
    ]
