import os
import django

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mywifipass.settings')  # Cambia 'django_x509.settings' por el módulo de configuración de tu proyecto
django.setup()

from mywifipass.models import WifiNetworkLocation

# Ruta de salida para los archivos
OUTPUT_DIR = "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

all_wifi_locations = WifiNetworkLocation.objects.all()
# Obtén el WifiNetworkLocation
wifi_location = all_wifi_locations[2]

# Obtén la CA asociada
ca = wifi_location.certificates_CA

# Escribe el certificado en un archivo
ca_cert_path = os.path.join(OUTPUT_DIR, f"{wifi_location.name}_ca_cert.pem")
with open(ca_cert_path, "w") as cert_file:
    cert_file.write(ca.certificate)

# Escribe la clave privada en un archivo
ca_key_path = os.path.join(OUTPUT_DIR, f"{wifi_location.name}_ca_key.pem")
with open(ca_key_path, "w") as key_file:
    key_file.write(ca.private_key)

print(f"CA certificate saved to: {ca_cert_path}")
print(f"CA private key saved to: {ca_key_path}")
