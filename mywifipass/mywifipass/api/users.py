# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

import logging
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.http import FileResponse

logger = logging.getLogger(__name__)
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

# Rate limiting imports
from mywifipass.api.throttles import (
    CertificateSigningThrottle,
    AuthorizationThrottle,
    DownloadThrottle,
    ValidationThrottle,
)

class WifiUserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a WifiUser.
    Networks will be assigned via M2M relation.
    """
    class Meta:
        model = WifiUser
        fields = ['name', 'email', 'id_document']
class WifiUserDetailSerializer(serializers.ModelSerializer):
    """
    Complete details of the WifiUser for a specific network.
    Network is provided in serializer context.
    """
    network_common_name = serializers.SerializerMethodField()
    ssid = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
    location_uuid = serializers.SerializerMethodField()
    is_user_authorized = serializers.SerializerMethodField()
    
    class Meta:
        model = WifiUser
        fields = [
            'user_uuid', 'name', 'email', 'id_document', 
            'has_attended', 'has_downloaded_pass', 'allow_access_expiration',
            'network_common_name', 'ssid', 'location', 'start_date', 'end_date',
            'description', 'location_name', 'location_uuid', 'certificates_symmetric_key', 'is_user_authorized'
        ]
        read_only_fields = ['user_uuid', 'allow_access_expiration']
    
    def get_network(self):
        """Get the network from context"""
        return self.context.get('network')
    
    def get_network_common_name(self, obj):
        network = self.get_network()
        if network and network.radius_Certificate:
            return network.radius_Certificate.common_name
        return None
    
    def get_ssid(self, obj):
        network = self.get_network()
        return network.SSID if network else None
    
    def get_location(self, obj):
        network = self.get_network()
        return network.location if network else None
    
    def get_start_date(self, obj):
        network = self.get_network()
        return network.start_date if network else None
    
    def get_end_date(self, obj):
        network = self.get_network()
        return network.end_date if network else None
    
    def get_description(self, obj):
        network = self.get_network()
        return network.description if network else None
    
    def get_location_name(self, obj):
        network = self.get_network()
        return network.name if network else None
    
    def get_location_uuid(self, obj):
        network = self.get_network()
        return network.location_uuid if network else None
    
    def get_is_user_authorized(self, obj):
        network = self.get_network()
        if network:
            return obj.is_authorized_for_network(network)
        return False
    
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
    """
    Serializer for downloading the WifiUser pass (WiFi credentials).
    Network is provided in serializer context.
    """
    email = serializers.EmailField(read_only=True)
    network_common_name = serializers.SerializerMethodField()
    ssid = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
    certificates_symmetric_key = serializers.SerializerMethodField()
    
    class Meta:
        model = WifiUser
        fields = [
            'email', 'network_common_name', 'ssid', 'location', 'start_date', 'end_date',
            'description', 'location_name', 'certificates_symmetric_key'
        ]

    def get_network(self):
        """Get the network from context"""
        return self.context.get('network')
    
    def get_network_common_name(self, obj):
        network = self.get_network()
        if network and network.radius_Certificate:
            return network.radius_Certificate.common_name
        return None
    
    def get_ssid(self, obj):
        network = self.get_network()
        return network.SSID if network else None
    
    def get_location(self, obj):
        network = self.get_network()
        return network.location if network else None
    
    def get_start_date(self, obj):
        network = self.get_network()
        return network.start_date if network else None
    
    def get_end_date(self, obj):
        network = self.get_network()
        return network.end_date if network else None
    
    def get_description(self, obj):
        network = self.get_network()
        return network.description if network else None
    
    def get_location_name(self, obj):
        network = self.get_network()
        return network.name if network else None

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
    # androidVersion = serializers.CharField()  # DEPRECATED: no longer tracked

class WifiUserViewSet(ModelViewSet):
    """
    ViewSet for CRUD operations on WifiUser within a network
    """
    lookup_field = 'user_uuid'
    swagger_tags = ['WiFi Users']  # Group users under "WiFi Users" in Swagger UI

    def get_network(self):
        """Retrieve the network from URL kwargs"""
        network_uuid = self.kwargs.get('network_location_uuid')
        if network_uuid:
            return get_object_or_404(WifiNetworkLocation, location_uuid=network_uuid)
        return None

    def get_queryset(self):
        """Filter users by network location (via M2M) if provided or list all users""" 
        network = self.get_network()
        if network:
            return WifiUser.objects.filter(networks=network)
        return WifiUser.objects.all()
    
    def get_serializer_context(self):
        """Add network to serializer context"""
        context = super().get_serializer_context()
        context['network'] = self.get_network()
        return context
    
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
        """Assign the network to the user (via M2M) when creating"""
        network = self.get_network()
        if network:
            user = serializer.save()
            user.networks.add(network)
        else:
            raise serializers.ValidationError("Network location UUID is required to create a user.")

    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['post'], permission_classes=[AllowAny], throttle_classes=[CertificateSigningThrottle])
    def sign_certificate(self, request, *args, **kwargs):
        from mywifipass.api.urls import USER_PATH 
        f"""POST {USER_PATH}sign_certificate/"""
        user = self.get_object()
        network = self.get_network()
        
        if not network:
            return Response({'error': 'Network location UUID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = SignCSRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csr_pem = serializer.validated_data['csr']
        # Pick the token and convert it from hex() to bytes
        token_hex = serializer.validated_data['token']
        token = bytes.fromhex(token_hex)    

        # Convert memoryview to bytes for comparison
        user_key = bytes(user.certificates_symmetric_key)
        # user.android_version = serializer.validated_data['androidVersion']  # DEPRECATED: no longer tracked

        if token != user_key:
            return Response({'error': 'Invalid token'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            signed_cert, ca_cert = user.sign_csr(csr_pem, network)
        except ValueError as e:
            # Log validation error for debugging; return generic message to client
            logger.warning(f"CSR validation failed for user {user.user_uuid}: {str(e)}")
            return Response({'error': 'Invalid certificate request. Please check your CSR format and try again.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log unexpected errors
            logger.exception(f"Unexpected error signing CSR for user {user.user_uuid}")
            return Response({'error': 'Certificate signing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        user.deauthorize()
        return Response({
            'signed_cert': signed_cert,
            'ca_cert': ca_cert
        }, status=status.HTTP_200_OK, headers={'Content-Type': 'application/json'})
    
    @swagger_auto_schema(tags = swagger_tags)
    @action(detail=True, methods=['get'], permission_classes=[AllowAny], throttle_classes=[DownloadThrottle])
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
    @action(detail=True, methods=['get'], permission_classes=[AllowAny], throttle_classes=[DownloadThrottle])
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
    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser], throttle_classes=[ValidationThrottle])
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
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], throttle_classes=[AuthorizationThrottle])
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
    @action(detail=True, methods=['get'], permission_classes=[AllowAny], throttle_classes=[ValidationThrottle])
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
    @action(detail=True, methods=['post'], permission_classes=[AllowAny], throttle_classes=[DownloadThrottle])
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