from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from getEAP_TLS.models import WifiUser, Ca, Cert, WifiNetworkLocation

def get_certificate_information (wifiuser: WifiUser, wifiNetworkLocation: WifiNetworkLocation):
    """ 
    Función que devuelve:
    - La clave privada del usuario
    - Su certificado
    - El certificado de la CA

    """
    json_data = {
        'user_name': wifiuser.certificate.common_name,
        'user_email': wifiuser.certificate.email,
        'user_id_document': wifiuser.id_document,
        'certificate': wifiuser.certificate.certificate,
        'private_key': wifiuser.certificate.private_key,
        'ca_certificate': wifiNetworkLocation.certificates_CA.certificate,    
        'network_common_name': wifiNetworkLocation.certificates_CA.common_name,
        'ssid': wifiNetworkLocation.SSID
    }
    return json_data

@api_view(['GET'])
def user(request):
    id = request.GET.get('id', '0')
    user = WifiUser.objects.get(id=id)
    wifiLocation = user.wifiLocation
    data = get_certificate_information(user, wifiLocation)
    return Response(data, status=status.HTTP_200_OK)