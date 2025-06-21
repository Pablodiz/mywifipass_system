#!/bin/bash

source "$(dirname "$0")/../.env"

# USES: 
# create_radius_openvpn_certificates.py 
# setup_openvpn_client.sh

# Create Openvpn client configuration directory and static address for the radius server
docker exec -it openvpn-server /bin/sh -c "mkdir -p /etc/openvpn/ccd"
docker exec -it openvpn-server /bin/sh -c "echo 'ifconfig-push 10.8.0.10 255.255.255.0' > /etc/openvpn/ccd/mywifipass-radius-server"

# Generate certificates and keys for OpenVPN
docker cp ./deploy_scripts/complementary_scripts/create_radius_openvpn_certificates.py openwisp-dashboard:/opt/openwisp
docker exec -it openwisp-dashboard /bin/sh -c "python3 /opt/openwisp/create_radius_openvpn_certificates.py" > openvpn_certificates.txt

# Create config file with variables
cat > temp_config.env <<EOF
HOST_SERVER_IP=$SERVER_IP
OPENVPN_PORT=1194
VPN_DOMAIN=openvpn.openwisp.org
EOF

# Generate OpenVPN configuration and copy it to the radius server
docker exec radius-server /bin/bash -c "mkdir -p /etc/openvpn/client"
docker cp ./openvpn_certificates.txt radius-server:/etc/openvpn/client/
docker cp ./temp_config.env radius-server:/etc/openvpn/client/config.env
docker cp ./deploy_scripts/complementary_scripts/setup_openvpn_client.sh radius-server:/etc/openvpn/client/
docker exec radius-server chmod +x /etc/openvpn/client/setup_openvpn_client.sh
docker exec radius-server /bin/bash /etc/openvpn/client/setup_openvpn_client.sh

# Cleanup
rm ./openvpn_certificates.txt
rm ./temp_config.env
