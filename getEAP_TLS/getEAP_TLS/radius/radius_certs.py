import os
from django_x509.models import Cert, Ca
from getEAP_TLS.models import WifiNetworkLocation

# Export directory
RADIUS_CERT_DIR = "/djangox509/getEAP_TLS/server_certs"

# We create the directory if it doesn't exist (it should)
if not os.path.exists(RADIUS_CERT_DIR):
    os.makedirs(RADIUS_CERT_DIR)


def export_wifi_location_certificates(wifi_location_id: int):
    """
    Exports the certificates for the radius server to use.
    """
    
    wifi_location = WifiNetworkLocation.objects.get(id=wifi_location_id)

    cert_path = os.path.join(RADIUS_CERT_DIR, f'server.pem')
    key_path = os.path.join(RADIUS_CERT_DIR, f'server.key')
    ca_path = os.path.join(RADIUS_CERT_DIR, f'ca.pem')
    
    with open(key_path, 'w') as key_file:
        key_file.write(wifi_location.radius_Certificate.private_key)

    with open(cert_path, 'w') as cert_file:
        cert_file.write(wifi_location.radius_Certificate.certificate)

    with open(ca_path, 'w') as ca_file:
        ca_file.write(wifi_location.certificates_CA.certificate)

