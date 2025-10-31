#!/bin/bash
# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.


# Get env variables from .env file
source "$(dirname "$0")/../.env"

# Generate shadow password for SSH
SSH_SHADOW=$(mkpasswd -m sha-512 $SSH_PASSWORD)
# Get API token  
TOKEN=$(curl -k -X POST $API_DOMAIN/api/v1/users/token/ -d "username=$USERNAME" -d "password=$PASSWORD" | jq -r .token)
# Get organizations
ORGANIZATIONS=$(curl -k -X GET $API_DOMAIN/api/v1/users/organization/ -H "Authorization: Bearer $TOKEN")
#get the ORG_UUID from the above json
ORG_UUID=$(echo $ORGANIZATIONS | jq -r '.results[0].id')
# Get OpenWISP secret
OWISP_SECRET=$(docker exec docker-openwisp-postgres-1 psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT shared_secret FROM config_organizationconfigsettings WHERE organization_id = '$ORG_UUID';" | sed -n '3p' | awk '{print $1}')

cat <<EOF > configure_openwisp.sh
#!/bin/ash 

exec > /tmp/log.txt 2>&1
set -x 

# execute with "sh ./configure_openwisp.sh &"

sed -i 's|^root:[^:]*:|root:$SSH_SHADOW:|' /etc/shadow

uci batch <<EOC
set network.lan.ipaddr=$INTERNAL_IP # change internal range so that if the one on WAN side is 192.168.1.1 there are no errors 
set network.lan.mask=$INTERNAL_MASK 
add firewall rule # add a rule for letting ssh through wan interface
set firewall.@rule[-1].name='Allow-SSH-WAN'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='tcp'
set firewall.@rule[-1].dest_port='22'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'
EOC

uci commit
/etc/init.d/network restart
/etc/init.d/firewall restart

cd /tmp
opkg update
opkg remove \$(opkg list-installed | grep '^wpad-' | cut -d' ' -f1) # We remove the current wpad package
opkg install wpad-openssl # Install wpad with EAP methods support
opkg install openvpn-openssl # Install OpenVPN for openwisp to use 

wget https://downloads.openwisp.io/openwisp-config/latest/openwisp-config_1.1.0-1_all.ipk
wget https://storage.googleapis.com/downloads.openwisp.io/openwisp-monitoring/latest/netjson-monitoring_0.2.1-1_all.ipk
wget https://storage.googleapis.com/downloads.openwisp.io/openwisp-monitoring/latest/openwisp-monitoring_0.2.1-1_all.ipk
opkg install openwisp-config_1.1.0-1_all.ipk
opkg install openwisp-monitoring_0.2.1-1_all.ipk
opkg install netjson-monitoring_0.2.1-1_all.ipk


echo "$SERVER_IP dashboard.openwisp.org api.openwisp.org openvpn.openwisp.org" | \
     tee -a /etc/hosts

MNG_IFACE=\$(uci get network.wan.device)

cat <<EOC > /etc/config/openwisp 
config controller 'http'
    option url '$DASHBOARD_DOMAIN'
    option verify_ssl '0'
    option shared_secret '$OWISP_SECRET'
    option management_interface '\$MNG_IFACE'
    option uuid ''
    option key ''
EOC

mkdir /etc/init.d/openwisp
/usr/sbin/openwisp-reload-config
/etc/init.d/openwisp-config restart
EOF
