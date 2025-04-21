from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import Http404, FileResponse
import uuid
from getEAP_TLS.models import WifiUser, WifiNetworkLocation
from getEAP_TLS.settings import BASE_URL, API_PATH, USER_PATH
from getEAP_TLS.utils import generate_qr_code

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

# Use of API TOKEN to configure an endpoint to only be used by authenticated admin users:
# from rest_framework.permissions import IsAdminUser
# from rest_framework.decorators import permission_classes
# Anotate the functio with:  
# @permission_classes([IsAdminUser])


# Cipher AES-256 in ECB mode (without IV)
def cipher_AES_256_ECB(plaintext: str, clave: bytes):
    if len(clave) != 32:
        raise ValueError("Key must be 32 bytes long for AES-256.")
    text_bytes = plaintext.encode()
    text_padded = pad(text_bytes, AES.block_size)  # Padding to 32 bytes
    cipher = AES.new(clave, AES.MODE_ECB)
    text_cifrado = cipher.encrypt(text_padded)
    return base64.b64encode(text_cifrado)



def replace_nulls(obj):
    if isinstance(obj, dict):
        return {k: replace_nulls(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nulls(v) for v in obj]
    elif obj is None:
        return ""
    return obj

def get_certificate_information (wifiuser: WifiUser, wifiNetworkLocation: WifiNetworkLocation):
    """ 
    Function to get the information of the user and the location
    Args:
        wifiuser: WifiUser object
        wifiNetworkLocation: WifiNetworkLocation object
    Returns:
        json_data: JSON object with the information of the user and the location
    """
    try: 
        key = wifiuser.certificates_symmetric_key
        # Encrypt the certificates with the symmetric key
        certificate = cipher_AES_256_ECB(wifiuser.certificate.certificate, key)
        private_key = cipher_AES_256_ECB(wifiuser.certificate.private_key, key)
        ca_certificate = cipher_AES_256_ECB(wifiNetworkLocation.certificates_CA.certificate, key)
    except Exception as e:
        raise ValueError("Error encrypting the certificates: " + str(e))

    json_data = {
        'user_name': wifiuser.name,
        'user_email': wifiuser.email,
        'user_id_document': wifiuser.id_document,
        'certificate': certificate,
        'private_key': private_key,
        'ca_certificate': ca_certificate,    
        'network_common_name': wifiNetworkLocation.certificates_CA.common_name,
        'ssid': wifiNetworkLocation.SSID,
        'user_uuid': wifiuser.user_uuid,
        'location': wifiNetworkLocation.location,
        'start_date': wifiNetworkLocation.start_date,
        'end_date': wifiNetworkLocation.end_date,
        'description': wifiNetworkLocation.description,
        'location_name': wifiNetworkLocation.name,
    }
    return replace_nulls(json_data)

@api_view(['GET'])
def user(request, uuid: uuid):
    try:
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        wifiLocation = user.wifiLocation
        data = get_certificate_information(user, wifiLocation)
        return Response(data, status=status.HTTP_200_OK, headers={'Content-Type': 'application/json'})
    except Http404: 
        return Response({'error': 'User with id ' + str(id)  + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def user_qr(request, uuid: uuid):
    """
    Handles the HTTP request to generate and return a QR code for a WifiUser.
    
    Args:
        request: The HTTP request object.
        uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        FileResponse: A response containing the QR code image.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        url = BASE_URL + API_PATH + USER_PATH + str(user.user_uuid) + "/"
        buffer = generate_qr_code(url)
        
        # Return the binary stream as a FileResponse
        response = FileResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = "inline"  # Ensure the image is displayed in the browser
        return response
    except Http404: 
        return Response({'error': 'User with id ' + str(uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def user_key(request, uuid:uuid):
    """
    Handles the HTTP request to retrieve the symmetric key for a WifiUser.
    
    Args:
        request: The HTTP request object.
        uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        Response: A response containing the symmetric key or an error message.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        certificates_symmetric_key = user.certificates_symmetric_key.hex()
        return Response({'certificates_symmetric_key': certificates_symmetric_key}, status=status.HTTP_200_OK)
    except Http404: 
        return Response({'error': 'User with id ' + str(uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)