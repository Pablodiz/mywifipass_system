from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from getEAP_TLS.models import WifiUser, Ca, Cert

@api_view(['GET'])
def hello(request):
    name = request.GET.get('name', 'guest')
    data = {
        'name': name,
        'message': f"Hello {name}, your first API endpoint has been created successfully!"
    }
    return Response(data, status=status.HTTP_200_OK)

def get_certificate_information (cert: Cert, ca: Ca):
    """ 
    Función que devuelve:
    - La clave privada del usuario
    - Su certificado
    - El certificado de la CA

    """
    json_data = {
        'name': cert.name,
        'certificate': cert.certificate,
        'private_key': cert.private_key,
        'ca_certificate': ca.certificate    
    }
    return json_data

@api_view(['GET'])
def user(request):
    id = request.GET.get('id', '0')
    user = WifiUser.objects.get(id=id)
    wifiLocation = user.wifiLocation
    data = {
        'ssid': wifiLocation.SSID,
    }

    certificate_information = get_certificate_information(user.certificate, wifiLocation.radius_CA)
    data.update(certificate_information) 

    return Response(data, status=status.HTTP_200_OK)