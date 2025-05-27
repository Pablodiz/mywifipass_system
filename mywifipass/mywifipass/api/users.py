from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import Http404, FileResponse
import uuid
from mywifipass.models import WifiUser, WifiNetworkLocation
from mywifipass.utils import generate_qr_code
import mywifipass.api.urls as urls 
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from rest_framework import serializers

# Use of API TOKEN to configure an endpoint to only be used by authenticated admin users:
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import permission_classes
# Anotate the function with:  
# @permission_classes([IsAdminUser])

from datetime import timedelta
from django.utils import timezone

from cryptography.hazmat.primitives.serialization import pkcs12, BestAvailableEncryption
from cryptography.hazmat.primitives import serialization
from cryptography import x509
import base64

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
    json_data = {
        'user_name': wifiuser.name,
        'user_email': wifiuser.email,
        'user_id_document': wifiuser.id_document,
        'user_uuid': wifiuser.user_uuid,
        'network_common_name': wifiNetworkLocation.certificates_CA.common_name,
        'ssid': wifiNetworkLocation.SSID,
        'location': wifiNetworkLocation.location,
        'start_date': wifiNetworkLocation.start_date,
        'end_date': wifiNetworkLocation.end_date,
        'description': wifiNetworkLocation.description,
        'location_name': wifiNetworkLocation.name,
        'location_uuid': wifiNetworkLocation.location_uuid,
        'certificates_symmetric_key': wifiuser.certificates_symmetric_key.hex(),
        'validation_url': urls.validation_url(wifiuser),
        'certificates_url': urls.certificates_url(wifiuser),
        'has_downloaded_url': urls.has_downloaded_url(wifiuser),
    }
    return replace_nulls(json_data)

@api_view(['GET'])
def user(request, user_uuid: uuid, **kwargs):
    try:
        user = get_object_or_404(WifiUser, user_uuid=user_uuid)
        if user.has_downloaded_pass is False: 
            wifiLocation = user.wifiLocation
            data = get_certificate_information(user, wifiLocation)
            return Response(data, status=status.HTTP_200_OK, headers={'Content-Type': 'application/json'})
        else: 
            return Response({'error': 'User has already downloaded the pass'}, status=status.HTTP_403_FORBIDDEN)
    except Http404: 
        return Response({'error': 'User with UUID ' + str(user_uuid)  + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def user_qr(request, user_uuid: uuid, **kwargs):
    """
    Handles the HTTP request to generate and return a QR code for a WifiUser.
    
    Args:
        request: The HTTP request object.
        uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        FileResponse: A response containing the QR code image.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=user_uuid)
        url = urls.user_url(user)
        buffer = generate_qr_code(url)
        
        # Return the binary stream as a FileResponse
        response = FileResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = "inline"  # Ensure the image is displayed in the browser
        return response
    except Http404: 
        return Response({'error': 'User with UUID ' + str(user_uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def user_key(request, user_uuid: uuid, **kwargs):
    """
    Handles the HTTP request to retrieve the symmetric key for a WifiUser.
    
    Args:
        request: The HTTP request object.
        uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        Response: A response containing the symmetric key or an error message.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=user_uuid)
        if user.allow_access_expiration is None:
            # If the user has never been allowed access, we return a 403 Forbidden response
            return Response({'error': 'User has never been allowed access'}, status=status.HTTP_403_FORBIDDEN)
        if user.allow_access_expiration > timezone.now() and user.certificate.revoked is False:
            certificates_symmetric_key = user.certificates_symmetric_key.hex()
            return Response({'certificates_symmetric_key': certificates_symmetric_key}, status=status.HTTP_200_OK)
        else: 
            # If the user is not allowed access, no password is return, instead we return a 403 Forbidden response
            return Response({'error': 'User is not allowed access'}, status=status.HTTP_403_FORBIDDEN)
    except Http404: 
        return Response({'error': 'User with UUID ' + str(user_uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAdminUser])
def check_user(request, user_uuid: uuid, **kwargs): 
    """
    Handles the HTTP request to receive data about a WifiUser and allow to get the password if the user is valid.
    
    Args:
        request: The HTTP request object.
        
        user_uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        Response: A response indicating whether the user is valid or not.
    """
    try:
        location_uuid = request.data.get('location_uuid')
        if not location_uuid:
            return Response({'error': 'location_uuid is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            location_uuid = uuid.UUID(location_uuid)
        except ValueError:
            return Response({'error': 'location_uuid must be a valid UUID.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = get_object_or_404(WifiNetworkLocation, location_uuid=location_uuid)
        except Http404:
            return Response({'error': f'Event with UUID {location_uuid} not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Buscar el usuario
        try:
            user = get_object_or_404(WifiUser, user_uuid=user_uuid, wifiLocation=event)
        except Http404:
            return Response({'error': f'User with UUID {user_uuid} not found for the specified event.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user has already accessed the event
        if user.has_attended:
            return Response({'error': 'User has already accessed the event.'}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'id_document': user.id_document,
            'name': user.name,
            'authorize_url': urls.authorize_url(user)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def allow_access_to_user(request, user_uuid: uuid, **kwargs): 
    """
    Handles the HTTP request to receive data about a WifiUser and allow to get the password if the user is valid.
    
    Args:
        request: The HTTP request object.
        
        user_uuid (uuid): The UUID of the WifiUser.
    
    Returns:
        Response: A response indicating whether the validation was done or not.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=user_uuid)
        if (user.certificate and user.certificate.revoked is False) or (user.certificate is None):
            user.has_attended = True
            user.allow_access_expiration = timezone.now() + timedelta(minutes=3)  # Set expiration to 5min from now
            user.save(send_email = False)
        else: 
            return Response({'error': 'User certificate is revoked.'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'message': 'The user can now join the network.'}, status=status.HTTP_200_OK)
    except serializers.ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Http404: 
        return Response({'error': 'User with UUID ' + str(user_uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def has_downloaded_pass(request, user_uuid: uuid, **kwargs):
    """
    Handles the HTTP request to set the has_downloaded_pass field of a WifiUser.
    
    Args:
        request: The HTTP request object.
    
    Returns:
        Response: A response indicating whether the operation was successful or not.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=user_uuid)
        user.has_downloaded_pass = True
        user.save(send_email = False)
        return Response({'message': 'The user has downloaded the pass.'}, status=status.HTTP_200_OK)
    except serializers.ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Http404: 
        return Response({'error': 'User with UUID ' + str(user_uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def generate_certificates(request, user_uuid: uuid, **kwargs):
    """
    Handles the HTTP request to generate certificates for a WifiUser.
    Returns a PKCS#12 file (base64-encoded) containing the user's certificate, private key, and CA.
    """
    try:
        user = get_object_or_404(WifiUser, user_uuid=user_uuid)
        if user.allow_access_expiration is None:
            return Response({'error': 'User has never been allowed access'}, status=status.HTTP_403_FORBIDDEN)
        if user.allow_access_expiration > timezone.now():
            customcert, certificate_pem, private_key_pem = user.create_certificate()
            user.certificate = customcert
            user.save(send_email=False)

            # Convert PEM to objects
            cert = x509.load_pem_x509_certificate(certificate_pem.encode())
            key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
            ca_cert = x509.load_pem_x509_certificate(user.wifiLocation.certificates_CA.certificate.encode())
            
            # Ensure the private key is in the correct format
            password = user.certificates_symmetric_key.hex()

            # Create PKCS#12
            p12_bytes = pkcs12.serialize_key_and_certificates(
                name=b"wifiuser",
                key=key,
                cert=cert,
                cas=[ca_cert],
                encryption_algorithm=BestAvailableEncryption(password.encode())
            )
            
            # Encode as base64 for transport
            p12_b64 = base64.b64encode(p12_bytes).decode()

            return Response({
                'pkcs12_b64': p12_b64
                }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'User is not allowed access'}, status=status.HTTP_403_FORBIDDEN)
    except Http404:
        return Response({'error': 'User with UUID ' + str(user_uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)