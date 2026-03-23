# Generated manually on 2026-03-23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mywifipass', '0009_migrate_wifiuser_networks_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='wifiuser',
            name='networks',
            field=models.ManyToManyField(help_text='Networks this user has access to', related_name='users_nm', to='mywifipass.wifinetworklocation'),
        ),
        migrations.AlterUniqueTogether(
            name='wifiuser',
            unique_together={('user_uuid', 'name')},
        ),
    ]
