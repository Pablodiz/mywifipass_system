#!/bin/bash
# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

SSID="$1"
CERTDIR="/etc/raddb/certs/$SSID"

# Remove EAP module
MOD_EAP="/etc/raddb/mods-available/eap-$SSID"
if [ -f "$MOD_EAP" ]; then
    rm "$MOD_EAP"
    echo "EAP module file for SSID '$SSID' removed."
else
    echo "EAP module file for SSID '$SSID' not found."
fi
if [ -L "/etc/raddb/mods-enabled/eap-$SSID" ]; then
    rm "/etc/raddb/mods-enabled/eap-$SSID"
    echo "EAP module symbolic link for SSID '$SSID' removed."
else
    echo "EAP module symbolic link for SSID '$SSID' not found."
fi

# Remove virtual server
SRV="/etc/raddb/sites-available/$SSID"
if [ -f "$SRV" ]; then
    rm "$SRV"
    echo "Virtual server file for SSID '$SSID' removed."
else
    echo "Virtual server file for SSID '$SSID' not found."
fi
if [ -L "/etc/raddb/sites-enabled/$SSID" ]; then
    rm "/etc/raddb/sites-enabled/$SSID"
    echo "Virtual server symbolic link for SSID '$SSID' removed."
else
    echo "Virtual server symbolic link for SSID '$SSID' not found."
fi

# Remove Realm from proxy.conf
# REALM_ENTRY="realm $SSID {
#   type = radius
#   virtual_server = $SSID
# }"
if [ -f "/etc/raddb/proxy.conf" ]; then
    sed -i "/^realm ${SSID} {/,/^}/d" /etc/raddb/proxy.conf
    echo "Realm for SSID '$SSID' removed from proxy.conf."
else
    echo "Proxy configuration file not found."
fi

echo "SSID '$SSID' removed."