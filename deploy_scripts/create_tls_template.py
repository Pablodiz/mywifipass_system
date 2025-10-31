# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import os
import sys
import django

# RADIUS_PORT, RADIUS_SERVER and RADIUS_SECRET need to be defined as env variables

# Add the project directory to PYTHONPATH
sys.path.append('/opt/openwisp/')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openwisp2.settings')
django.setup()

# Import models
from openwisp_controller.config.models import Template
from openwisp_users.models import Organization, User

radius_secret = os.environ.get("RADIUS_SECRET", "")
if not radius_secret:
    raise ValueError("RADIUS_SECRET environment variable is not set.")

radius_port = os.environ.get('RADIUS_PORT', 10812)
if not radius_port.isdigit():
    raise ValueError("RADIUS_PORT environment variable must be a number.")

radius_port = int(radius_port)

radius_server = os.environ.get('RADIUS_SERVER', "radius-server")


# Load your JSON configuration
config_json = {
    "interfaces": [
        {
            "wireless": {
                "network": ["lan"],
                "mode": "access_point",
                "radio": "radio0",
                "ssid": "TLS_Wifi",
                "encryption": {
                    "protocol": "wpa2_enterprise",
                    "key": radius_secret,
                    "disabled": False,
                    "cipher": "auto",
                    "ieee80211x": "1",
                    "server": radius_server,
                    "port": radius_port,
                },
            },
            "type": "wireless",
            "name": "wlan0opkg install freeradius3",
            "disabled": False,
            "autostart": True,
        }
    ],
    "radios": [
        {
            "name": "radio0",
            "protocol": "802.11n",
            "channel": 1,
            "channel_width": 20,
            "country": "ES",
            "disabled": False,
            "driver": "mac80211",
            "hwmode": "11g",
            "band": "2g",
        }
    ]
}

# Get user and organization (adjust to your environment)
user = User.objects.get(username='admin')  # or by ID
organization = Organization.objects.first()  # or select as needed

# Create the template
Template.objects.create(
    name='EAP-TLS Template',
    config=config_json,
    organization=organization,
    type='generic',
    default=True,
    required=False,
    auto_cert=False,
    backend='netjsonconfig.OpenWrt',
    default_values={},
)

print("Template created successfully.")


# Docker CP + docker exec ... python3...

#docker exec -it -e RADIUS_PORT=1812 -e RADIUS_SERVER=10.8.0.10 -e RADIUS_SECRET=$(cat django-x509/our_radius/RADIUS_SECRET/secret.txt) docker-openwisp-dashboard-1 python3 create_tls_template.py
