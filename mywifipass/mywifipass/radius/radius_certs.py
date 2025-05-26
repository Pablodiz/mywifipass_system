import os
from mywifipass.models import WifiNetworkLocation, MyCustomCert

# Export directory
RADIUS_PENDING_CERT_DIR = "/djangox509/mywifipass/server_certs/pending"
RADIUS_PROCESSED_CERT_DIR = "/djangox509/mywifipass/server_certs/processed"
RADIUS_DELETION_CERT_DIR = "/djangox509/mywifipass/server_certs/deletion"
RADIUS_UPDATE_CRL = "/djangox509/mywifipass/server_certs/update_crl"

def export_certificates(wifiLocation: WifiNetworkLocation):
    """
    Creates and exports the certificates for the radius server to use.
    """
    # We create the directories if they don't exist (they should)
    if not os.path.exists(RADIUS_PENDING_CERT_DIR):
        os.makedirs(RADIUS_PENDING_CERT_DIR)

    if not os.path.exists(RADIUS_PROCESSED_CERT_DIR):
        os.makedirs(RADIUS_PROCESSED_CERT_DIR)

    ssid_path = os.path.join(RADIUS_PENDING_CERT_DIR, f'{wifiLocation.SSID.replace(" ", "_")}')
    
    # We create the directorie for the SSID if it doesn't exist
    if not os.path.exists(ssid_path):
        os.makedirs(ssid_path)

    cert_path = os.path.join(ssid_path, f'server.pem')
    key_path = os.path.join(ssid_path, f'server.key')
    ca_path = os.path.join(ssid_path, f'ca.pem')
    crl_path = os.path.join(ssid_path, f'crl.pem') # It will be empty but it must exist
    
    # We create the certificates: 
    ca = wifiLocation.certificates_CA
    if ca: 
        # Create the radius certificate
        radius_custom_cert = MyCustomCert(
            name=f"{wifiLocation.name}'s Radius Certificate",
            ca=ca,
            common_name=wifiLocation.name,
            validity_start=ca.validity_start,
            validity_end=ca.validity_end,
        )
        certificate, private_key = radius_custom_cert.save(return_cert_fields=True)
        wifiLocation.radius_Certificate = radius_custom_cert

        with open(ca_path, 'w') as ca_file:
            ca_file.write(ca.certificate)

        with open(key_path, 'w') as key_file:
            key_file.write(private_key)

        with open(cert_path, 'w') as cert_file:
            cert_file.write(certificate)
        
        with open(crl_path, 'w') as crl_file:
            crl_file.write(ca.crl.decode('utf-8'))

def mark_ssid_for_deletion(wifiLocation: WifiNetworkLocation):
    """
    Marks an SSID for deletion by creating a file with its name in the deletion directory.
    """
    ssid_path = os.path.join(RADIUS_DELETION_CERT_DIR, f'{wifiLocation.SSID.replace(" ", "_")}')
    # We create a file with the SSID name in the deletion directory
    with open(ssid_path, 'w') as ssid_file:
        ssid_file.write(wifiLocation.SSID)

    wifiLocation.radius_Certificate.delete()
    wifiLocation.radius_Certificate = None

def mark_ssid_to_update_crl(wifiLocation: WifiNetworkLocation):
    """
    Marks an SSID for update CRL by creating a file with its name in the deletion directory.
    """
    ssid_path = os.path.join(RADIUS_UPDATE_CRL, f'{wifiLocation.SSID.replace(" ", "_")}')
    # We create a file with the SSID name in the update_crl directory
    with open(ssid_path, 'w') as ssid_file:
        ssid_file.write(wifiLocation.SSID)