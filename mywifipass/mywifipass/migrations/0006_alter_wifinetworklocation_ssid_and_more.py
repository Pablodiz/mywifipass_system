# Generated by Django 5.1.9 on 2025-06-01 11:05

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mywifipass', '0005_alter_wifinetworklocation_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wifinetworklocation',
            name='SSID',
            field=models.CharField(max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='wifinetworklocation',
            name='end_date',
            field=models.DateField(blank=True, default=datetime.date(2035, 6, 1), null=True),
        ),
        migrations.AlterField(
            model_name='wifinetworklocation',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
