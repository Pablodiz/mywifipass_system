from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from mywifipass.models import WifiUser, WifiNetworkLocation
from mywifipass.utils import generate_qr_code
import mywifipass.api.urls as urls 
import base64

# Use of API TOKEN to configure an endpoint to only be used by authenticated admin users:
from rest_framework.permissions import IsAdminUser, AllowAny

from datetime import timedelta
from django.utils import timezone

from cryptography.hazmat.primitives.serialization import pkcs12, BestAvailableEncryption
from cryptography.hazmat.primitives import serialization
from cryptography import x509
import base64

from drf_yasg.utils import swagger_auto_schema

class WifiUserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a WifiUser.
    """
    class Meta:
        model = WifiUser
        fields = ['name', 'email', 'id_document', 'wifiLocation']
class WifiUserDetailSerializer(serializers.ModelSerializer):
    """Complete details of the WifiUser """
    network_common_name = serializers.CharField(source='wifiLocation.radius_Certificate.common_name', read_only=True)
    ssid = serializers.CharField(source='wifiLocation.SSID', read_only=True)
    location = serializers.CharField(source='wifiLocation.location', read_only=True)
    start_date = serializers.DateField(source='wifiLocation.start_date', read_only=True)
    end_date = serializers.DateField(source='wifiLocation.end_date', read_only=True)
    description = serializers.CharField(source='wifiLocation.description', read_only=True)
    location_name = serializers.CharField(source='wifiLocation.name', read_only=True)
    location_uuid = serializers.UUIDField(source='wifiLocation.location_uuid', read_only=True)                   
    class Meta:
        model = WifiUser
        fields = [
            'user_uuid', 'name', 'email', 'id_document', 
            'has_attended', 'has_downloaded_pass', 'allow_access_expiration',
            'network_common_name', 'ssid', 'location', 'start_date', 'end_date',
            'description', 'location_name', 'location_uuid', 'certificates_symmetric_key', 'is_user_authorized'
        ]
        read_only_fields = ['user_uuid', 'allow_access_expiration']
    
class WifiUserListSerializer(serializers.ModelSerializer):
    """Serializer for listing WifiUsers with basic information."""
    class Meta:
        model = WifiUser
        fields = ['user_uuid', 'name', 'email', 'has_attended', 'has_downloaded_pass']


class WifiUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating WifiUser information."""
    class Meta:
        model = WifiUser
        fields = ['user_uuid', 'name', 'email', 'has_attended', 'has_downloaded_pass']

class WifiUserWifiPassSerializer(serializers.ModelSerializer):
    """Serializer for downloading the WifiUser pass."""
    email = serializers.EmailField(read_only=True)
    network_common_name = serializers.CharField(source='wifiLocation.radius_Certificate.common_name', read_only=True)
    ssid = serializers.CharField(source='wifiLocation.SSID', read_only=True)
    location = serializers.CharField(source='wifiLocation.location', read_only=True)
    start_date = serializers.DateField(source='wifiLocation.start_date', read_only=True)
    end_date = serializers.DateField(source='wifiLocation.end_date', read_only=True)
    description = serializers.CharField(source='wifiLocation.description', read_only=True)
    location_name = serializers.CharField(source='wifiLocation.name', read_only=True)
    certificates_symmetric_key = serializers.SerializerMethodField()
    class Meta:
        model = WifiUser
        fields = [
            'email', 'network_common_name', 'ssid', 'location', 'start_date', 'end_date',
            'description', 'location_name', 'certificates_symmetric_key'
        ]

    def get_certificates_symmetric_key(self, obj):
        """Return the symmetric key for the user's certificates."""
        if obj.certificates_symmetric_key:
            return obj.certificates_symmetric_key.hex()
        return None


class CheckUserSerializer(serializers.Serializer):
    """For checking user information before authorizing"""
    id_document = serializers.CharField()
    name = serializers.CharField()
    authorize_url = serializers.URLField()

class SignCSRSerializer(serializers.Serializer):
    """For signing a CSR"""
    csr = serializers.CharField()
    token = serializers.CharField()

class WifiUserViewSet(ModelViewSet):
    """
    ViewSet for CRUD operations on WifiUser within a network
    """
    lookup_field = 'user_uuid'
    swagger_tags = ['WiFi Users']  # Group users under "WiFi Users" in Swagger UI

    def get_queryset(self):
        """Filter users by network location UUID if provided or list all users""" 
        network_uuid = self.kwargs.get('network_location_uuid')
        if network_uuid:
            return WifiUser.objects.filter(wifiLocation__location_uuid=network_uuid)
        return WifiUser.objects.all()
    
    def get_serializer_class(self):
        """Select serializers"""
        if self.action == 'create':
            return WifiUserCreateSerializer
        elif self.action == 'list':
            return WifiUserListSerializer
        elif self.action in ['update', 'partial_update']:
            return WifiUserUpdateSerializer
        elif self.action == 'check_user':
            return CheckUserSerializer
        elif self.action == 'download': 
            return WifiUserWifiPassSerializer
        else:  # retrieve
            return WifiUserDetailSerializer
    
    def get_permissions(self):
        """Select permissions for each action"""
        if self.action in ['create', 'check_user', 'authorize','update', 'partial_update', 'destroy', 'list', 'retrieve']:
            permission_classes = [IsAdminUser]  
        else:
            permission_classes = [AllowAny]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Asign the network location to the user when creating"""
        network_uuid = self.kwargs.get('network_location_uuid')
        if network_uuid:
            network = get_object_or_404(WifiNetworkLocation, location_uuid=network_uuid)
            serializer.save(wifiLocation=network)
        else:
            raise serializers.ValidationError("Network location UUID is required to create a user.")

    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def sign_certificate(self, request, *args, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""POST {USER_PATH}sign_certificate/"""
        user = self.get_object()
        serializer = SignCSRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csr_pem = serializer.validated_data['csr']
        # Pick the token and convert it from hex() to bytes
        token_hex = serializer.validated_data['token']
        token = bytes.fromhex(token_hex)    

        # Convert memoryview to bytes for comparison
        user_key = bytes(user.certificates_symmetric_key)

        if token != user_key:
            return Response({'error': 'Invalid token'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            signed_cert, ca_cert = user.sign_csr(csr_pem)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        user.deauthorize()
        return Response({
            'signed_cert': signed_cert,
            'ca_cert': ca_cert
        }, status=status.HTTP_200_OK, headers={'Content-Type': 'application/json'})
    
    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def download(self, request, *args, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""GET {USER_PATH}download/"""
        user = self.get_object()
        if user.has_downloaded_pass:
            return Response(
                {'error': 'User has already downloaded the pass'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(user)
        data = serializer.data
        
        # Add urls to the response data
        data.update({
            'validation_url': urls.validation_url(user),
            'certificates_url': urls.sign_certificate_url(user),
            'has_downloaded_url': urls.has_downloaded_url(user),
            'check_user_authorized_url': urls.check_user_authorized_url(user),
            'is_user_authorized': user.is_user_authorized
        })
        
        return Response(data, status=status.HTTP_200_OK, headers={'Content-Type': 'application/json'})
    
    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def qr(self, request, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""GET {USER_PATH}qr/"""
        user = self.get_object()
        url = urls.email_url(user)
        buffer = generate_qr_code(url)
        
        response = FileResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = "inline"
        return response
    
    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def validate(self, request, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""GET {USER_PATH}validate/"""
        user = self.get_object()
        
        if user.has_attended:
            return Response(
                {'error': 'User has already accessed the event.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = {
            'id_document': user.id_document,
            'name': user.name,
            'authorize_url': urls.authorize_url(user)
        }
        return Response(data)
    
    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def authorize(self, request, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""POST {USER_PATH}authorize/"""
        user = self.get_object()
        
        if user.certificate and user.certificate.revoked:
            return Response(
                {'error': 'User certificate is revoked.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user.has_attended = True
        user.allow_access_expiration = timezone.now() + timedelta(minutes=3)
        user.save(send_email=False)
        
        return Response({'message': 'The user can now join the network.'})
        
    # @swagger_auto_schema(tags = swagger_tags)
    # @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    # def certificates(self, request, **kwargs):
    #     from mywifipass.api.urls import USER_PATH 
    #     f"""GET {USER_PATH}certificates/"""
    #     user = self.get_object()
        
    #     Check if the network requires validator
    #     if user.wifiLocation.requires_validator:
    #         User needs to be validated by admin
    #         if not user.allow_access_expiration or user.allow_access_expiration <= timezone.now():
    #             return Response(
    #                 {'error': 'User is not allowed to access'}, 
    #                 status=status.HTTP_403_FORBIDDEN
    #             )
    #     If network doesn't require validator, skip validation check
        
    #     Generate certs
    #     customcert, certificate_pem, private_key_pem = user.create_certificate()
    #     user.certificate = customcert
    #     if user.wifiLocation.requires_validator:
    #         Only reset expiration if network requires validator
    #         user.allow_access_expiration = None
    #     user.save(send_email=False)
        
    #     Convert to objects used by pkcs12
    #     cert = x509.load_pem_x509_certificate(certificate_pem.encode())
    #     key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    #     ca_cert = x509.load_pem_x509_certificate(user.wifiLocation.certificates_CA.certificate.encode())
        
    #     Serialize to PKCS#12 protecting with symmetric key
    #     password = user.certificates_symmetric_key.hex()
    #     p12_bytes = pkcs12.serialize_key_and_certificates(
    #         name=b"wifiuser",
    #         key=key,
    #         cert=cert,
    #         cas=[ca_cert],
    #         encryption_algorithm=BestAvailableEncryption(password.encode())
    #     )
        
    #     p12_b64 = base64.b64encode(p12_bytes).decode()
    #     return Response({'pkcs12_b64': p12_b64}, status=status.HTTP_200_OK, headers={'Content-Type': 'application/json'})
    
    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def check_user_authorized(self, request, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""GET {USER_PATH}check_user_authorized/"""
        user = self.get_object()
        
        if not user.is_user_authorized:
            return Response(
                {'error': 'User is not allowed to access'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({'message': 'User is authorized to access the network.'})

    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def downloaded(self, request, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""POST {USER_PATH}downloaded/"""
        user = self.get_object()
        user.has_downloaded_pass = True
        user.save(send_email=False)
        return Response({'message': 'The user has downloaded the pass.'})

    @swagger_auto_schema(tags = swagger_tags)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags = swagger_tags)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags = swagger_tags)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags = swagger_tags)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags = swagger_tags)
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags = swagger_tags)
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)