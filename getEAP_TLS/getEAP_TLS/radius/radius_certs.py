import os
from getEAP_TLS.models import WifiNetworkLocation

# Export directory
RADIUS_PENDING_CERT_DIR = "/djangox509/getEAP_TLS/server_certs/pending"
RADIUS_PROCESSED_CERT_DIR = "/djangox509/getEAP_TLS/server_certs/processed"

def export_certificates(wifiLocation: WifiNetworkLocation):
    """
    Exports the certificates for the radius server to use.
    """
    # We create the directories if they don't exist (they should)
    if not os.path.exists(RADIUS_PENDING_CERT_DIR):
        os.makedirs(RADIUS_PENDING_CERT_DIR)

    if not os.path.exists(RADIUS_PROCESSED_CERT_DIR):
        os.makedirs(RADIUS_PROCESSED_CERT_DIR)

    ssid_path = os.path.join(RADIUS_PENDING_CERT_DIR, f'{wifiLocation.SSID}')
    
    # We create the directorie for the SSID if it doesn't exist
    if not os.path.exists(ssid_path):
        os.makedirs(ssid_path)

    cert_path = os.path.join(ssid_path, f'server.pem')
    key_path = os.path.join(ssid_path, f'server.key')
    ca_path = os.path.join(ssid_path, f'ca.pem')
    
    with open(key_path, 'w') as key_file:
        key_file.write(wifiLocation.radius_Certificate.private_key)

    with open(cert_path, 'w') as cert_file:
        cert_file.write(wifiLocation.radius_Certificate.certificate)

    with open(ca_path, 'w') as ca_file:
        ca_file.write(wifiLocation.certificates_CA.certificate)

