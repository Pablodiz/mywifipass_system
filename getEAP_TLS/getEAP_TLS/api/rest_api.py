from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import Http404, FileResponse, HttpResponse
import uuid
from getEAP_TLS.models import WifiUser, WifiNetworkLocation
from getEAP_TLS.settings import BASE_URL, API_PATH, USER_PATH
from getEAP_TLS.utils import generate_qr_code
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from rest_framework import serializers

# Use of API TOKEN to configure an endpoint to only be used by authenticated admin users:
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import permission_classes
# Anotate the function with:  
# @permission_classes([IsAdminUser])


def user_url (user_uuid):
    """
    Function to get the URL of the user
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL of the user
    """
    return BASE_URL + API_PATH + USER_PATH + str(user_uuid) 

def user_qr_url (user_uuid):
    """
    Function to get the URL of the user QR code
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL of the user QR code
    """
    return BASE_URL + API_PATH + "user_qr/" + str(user_uuid) 

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


def certificates_symmetric_key_url(user_uuid: uuid):
    """
    Function to get the URL of the symmetric key of the user
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL of the symmetric key of the user
    """
    return user_url(user_uuid) + "/key"

def validation_url(user_uuid: uuid):
    """
    Function to get the URL of the validation of the user
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL of the validation of the user
    """
    return user_url(user_uuid) + "/validate"

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
        'user_uuid': wifiuser.user_uuid,
        'certificate': certificate,
        'private_key': private_key,
        'ca_certificate': ca_certificate,    
        'network_common_name': wifiNetworkLocation.certificates_CA.common_name,
        'ssid': wifiNetworkLocation.SSID,
        'location': wifiNetworkLocation.location,
        'start_date': wifiNetworkLocation.start_date,
        'end_date': wifiNetworkLocation.end_date,
        'description': wifiNetworkLocation.description,
        'location_name': wifiNetworkLocation.name,
        'validation_url': validation_url(wifiuser.user_uuid),
        'certificates_symmetric_key_url': certificates_symmetric_key_url(wifiuser.user_uuid),
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
        url = user_url(user.user_uuid)
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
        if user.allow_access:
            certificates_symmetric_key = user.certificates_symmetric_key.hex()
            return Response({'certificates_symmetric_key': certificates_symmetric_key}, status=status.HTTP_200_OK)
        else: 
            # If the user is not allowed access, no password is return, instead we return a 403 Forbidden response
            return Response({'error': 'User is not allowed access'}, status=status.HTTP_403_FORBIDDEN)
    except Http404: 
        return Response({'error': 'User with id ' + str(uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidateUserSerializer(serializers.Serializer):
    """
    Serializer for validating a WifiUser.
    """
    user_uuid = serializers.UUIDField(required=True)
    user_name = serializers.CharField(required=True)
    user_email = serializers.EmailField(required=True)
    user_id_document = serializers.CharField(required=True)

    def validate(self, data):
        """
        Validate the user.
        """
        user_uuid = data.get('user_uuid')
        user_name = data.get('user_name')
        user_email = data.get('user_email')
        user_id_document = data.get('user_id_document')

        try:
            user = WifiUser.objects.get(
                user_uuid=user_uuid,
                name=user_name,
                email=user_email,
                id_document=user_id_document
            )
            if user:
                return data
            else:
                raise serializers.ValidationError("User is not valid.")
        except WifiUser.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        except Exception as e:
            raise serializers.ValidationError(f"An error occurred: {str(e)}")
        
@api_view(['POST'])
@permission_classes([IsAdminUser])
def validate_user(request, uuid:uuid): 
    """
    Handles the HTTP request to receive data about a WifiUser and allow to get the password if the user is valid.
    
    Args:
        request: The HTTP request object.
        
        uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        Response: A response indicating whether the user is valid or not.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        request_data = request.data 
        serializer = ValidateUserSerializer(data=request_data)
        if serializer.is_valid():
            user.allow_access = True
            user.save()
            return Response({'message': 'User is valid and access is allowed.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    except serializers.ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Http404: 
        return Response({'error': 'User with id ' + str(uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def show_crl(request, id:int):
    """
    Handles the HTTP request to show the Certificate Revocation List (CRL) of an event.
    
    Args:
        request: The HTTP request object.
    
    Returns:
        Response: A response containing the CRL or an error message.
    """
    try:
        event = get_object_or_404(WifiNetworkLocation, id=id)
        crl = event.certificates_CA.crl
        if crl:
            crl_text = crl.decode('utf-8')
            print(crl_text)
            return HttpResponse(crl_text, content_type="text/plain", status=status.HTTP_200_OK) # We use an HttpResponse to return the CRL as a text file
        else:
            return Response({'error': 'No CRL found for this event.'}, status=status.HTTP_404_NOT_FOUND)
    except Http404:
        return Response({'error': 'Event with id ' + str(id) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    