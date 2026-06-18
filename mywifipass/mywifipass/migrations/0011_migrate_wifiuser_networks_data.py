# Generated manually on 2026-03-23

from django.db import migrations


def migrate_wifilocation_to_networks(apps, schema_editor):
    """
    Migrate data from wifiLocation FK to networks M2M.
    For each WifiUser that has a wifiLocation, add that network to their networks M2M.
    """
    WifiUser = apps.get_model('mywifipass', 'WifiUser')
    
    count = 0
    for user in WifiUser.objects.filter(wifiLocation__isnull=False):
        # Add the current wifiLocation to the networks M2M
        user.networks.add(user.wifiLocation)
        count += 1
    
    print(f"Migrated {count} users from wifiLocation to networks M2M")


def reverse_migrate(apps, schema_editor):
    """
    Reverse migration: clear networks M2M (but keep wifiLocation for safety)
    """
    WifiUser = apps.get_model('mywifipass', 'WifiUser')
    for user in WifiUser.objects.all():
        user.networks.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('mywifipass', '0010_add_networks_m2m'),
    ]

    operations = [
        migrations.RunPython(migrate_wifilocation_to_networks, reverse_migrate),
    ]
