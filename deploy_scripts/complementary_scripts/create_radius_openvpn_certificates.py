import os
import sys
import django 
import warnings
warnings.filterwarnings("ignore")

# Add the project directory to PYTHONPATH
sys.path.append('/opt/openwisp/')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openwisp2.settings')
django.setup()

from openwisp_controller.pki.models import Cert, Ca

ca = Ca.objects.get(name="default")

cert = Cert.objects.filter(name="mywifipass-radius-server").first()
if cert is not None:
    cert.delete()
server_extensions = [
    {"name": "extendedKeyUsage", "value": "clientAuth", "critical": False}
]
cert = Cert.objects.create(
    name = "mywifipass-radius-server", 
    ca=ca,
    key_length=ca.key_length,
    digest=ca.digest,
    country_code=ca.country_code,
    state=ca.state,
    city=ca.city,
    organization_name=ca.organization_name,
    common_name="mywifipass-radius-server",
    extensions=server_extensions,
)

# Change the vpn template
from openwisp_controller.config.models import Vpn 
vpn = Vpn.objects.get(name="default")
vpn.config['openvpn'][0]['topology']='subnet'
vpn.config['openvpn'][0]['client_to_client']=True
vpn.config['openvpn'][0]['client-config-dir']='/etc/openvpn/ccd'
vpn.save()

print(ca.certificate) 
print(cert.certificate)
print(cert.private_key)

# >>> vpn.config['openvpn'][0]['client-config-dir']='/etc/openvpn/ccd'