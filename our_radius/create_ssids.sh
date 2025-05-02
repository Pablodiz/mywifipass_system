#!/bin/bash
SSID="$1"
CERTDIR="/etc/raddb/certs/$SSID"

# Create EAP module
MOD_EAP="/etc/raddb/mods-available/eap-$SSID"
cp /etc/raddb/mods-available/eap-template "$MOD_EAP"
sed -i "s/__SSID__/$SSID/g" "$MOD_EAP"
ln -s "../mods-available/eap-$SSID" "/etc/raddb/mods-enabled/eap-$SSID"
echo "EAP module for SSID '$SSID' created."

# Create virtual server
SRV="/etc/raddb/sites-available/$SSID"
cp /etc/raddb/sites-available/server-template "$SRV"
sed -i "s/__SSID__/$SSID/g" "$SRV"
ln -s "../sites-available/$SSID" "/etc/raddb/sites-enabled/$SSID"
echo "Virtual server for SSID '$SSID' created."

# Add Realm to proxy.conf
REALM_ENTRY="realm $SSID {
  type = radius
  virtual_server = $SSID
}"
grep -q "realm $SSID" /etc/raddb/proxy.conf || echo "$REALM_ENTRY" >> /etc/raddb/proxy.conf
echo "Realm for SSID '$SSID' added to proxy.conf."

echo "SSID '$SSID' registered."