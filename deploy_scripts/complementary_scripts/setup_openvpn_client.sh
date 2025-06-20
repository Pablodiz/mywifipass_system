#!/bin/bash

CONFIG_FILE="$(dirname "$0")/config.env"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Config file $CONFIG_FILE not found"
    exit 1
fi

FOLDER="/etc/openvpn/client"

if ! grep -q "$HOST_SERVER_IP $VPN_DOMAIN" /etc/hosts; then
  echo "$HOST_SERVER_IP $VPN_DOMAIN" >> /etc/hosts
fi

# Install openvpn 
apt update && apt install -y openvpn

# Obtain certificates and keys for OpenVPN client
CERT_FILE="$FOLDER/openvpn_certificates.txt"

# Extract all CERTIFICATE blocks
sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' "$CERT_FILE" > allcerts.tmp

# Extract CA certificate (first block)
sed -n '1,/-----END CERTIFICATE-----/p' allcerts.tmp > $FOLDER/ca.pem

# Extract client certificate (second block)
sed -n '0,/-----END CERTIFICATE-----/d;1,/-----END CERTIFICATE-----/p' allcerts.tmp > $FOLDER/client.pem

# Remove temp file
rm allcerts.tmp

# Extract private key
sed -n '/-----BEGIN PRIVATE KEY-----/,/-----END PRIVATE KEY-----/p' "$CERT_FILE" > $FOLDER/client.key

# create OpenVPN client configuration file (obtained from the options applied to the openwrt aps)
cat > $FOLDER/client.conf <<EOF
client
dev tun0
dev-type tun
proto udp
remote $VPN_DOMAIN $SERVER_PORT
persist-key
persist-tun
ca $FOLDER/ca.pem
cert $FOLDER/client.pem
key $FOLDER/client.key
auth SHA1
comp-lzo no
user nobody
group nogroup
resolv-retry infinite
keepalive 10 120
fast-io
pull
script-security 2
mute 0
reneg-sec 0
mssfix 1450
mode p2p
nobind
persist-key
persist-tun
verb 3
float
EOF

chmod 600 $FOLDER/client.key


CRON_LINE="*/1 * * * * if [ ! \`pgrep openvpn\` ]; then /usr/sbin/openvpn --config $FOLDER/client.conf >> $FOLDER/openvpn.log 2>&1; fi"
if ! crontab -l 2>/dev/null | grep -F -q "$CRON_LINE"; then
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
fi