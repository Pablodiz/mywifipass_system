from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import Http404
import uuid
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
def user(request, uuid: uuid):
    try:
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        wifiLocation = user.wifiLocation
        data = get_certificate_information(user, wifiLocation)
        return Response(data, status=status.HTTP_200_OK)
    except Http404: 
        return Response({'error': 'User with id ' + str(id)  + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
