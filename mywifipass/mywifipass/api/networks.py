from rest_framework.response import Response
from rest_framework import status, serializers
from django.http import HttpResponse
from mywifipass.models import WifiNetworkLocation
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
class WifiNetworkLocationSerializer(serializers.ModelSerializer):
    """Detailed serializer for WifiNetworkLocation, used for all operations except listing."""
    class Meta:
        model = WifiNetworkLocation
        fields = [
            'name', 'SSID',
            'location', 'description', 'brief_description', 'start_date', 'end_date',
            'form_link', 'is_registration_open', 'is_enabled_in_radius', 
            'is_visible_in_web', 'requires_validator', 'send_emails_automatically', 'logo', 'location_uuid'
        ]
        extra_kwargs = {
            # Optional fields
            'location': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'brief_description': {'required': False, 'allow_blank': True},
            'start_date': {'required': False, 'allow_null': True},
            'end_date': {'required': False, 'allow_null': True},
            'form_link': {'required': False, 'allow_blank': True},
            'is_registration_open': {'required': False},
            'is_enabled_in_radius': {'required': False},
            'is_visible_in_web': {'required': False},
            'requires_validator': {'required': False},
            'send_emails_automatically': {'required': False},
            'logo': {'required': False, 'allow_null': True},
            'location_uuid': {'read_only': True},
        }

class WifiNetworkLocationSerializerForList(serializers.ModelSerializer):
    """For listing WifiNetworkLocation"""
    class Meta:
        model = WifiNetworkLocation
        fields = [
            'location_uuid', 'name'
        ]

class WifiNetworkLocationViewSet(ModelViewSet):
    """
    ViewSet for CRUD operations on WifiNetworkLocation
    """
    queryset = WifiNetworkLocation.objects.all()
    lookup_field = 'location_uuid'
    swagger_tags = ['Wifi Network Locations']

    def get_permissions(self):
        """ Returns the appropriate permissions based on the action being performed."""
        if self.action in ['create','update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action == 'crl':
            permission_classes = [AllowAny]  
        else:  # list, retrieve
            permission_classes = [IsAdminUser]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """ Returns the appropriate serializer class based on the action being performed."""
        if self.action == 'list':
            return WifiNetworkLocationSerializerForList
        else:
            return WifiNetworkLocationSerializer
    
    @swagger_auto_schema(tags=swagger_tags)
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def crl(self, request, **kwargs):
        from mywifipass.api.urls import NETWORK_PATH
        f"""GET {NETWORK_PATH}/crl/
        Returns the Certificate Revocation List (CRL) for the specified network.
        """
        try:
            event = self.get_object()
            crl = event.certificates_CA.crl
            if crl:
                crl_text = crl.decode('utf-8')
                return HttpResponse(crl_text, content_type="text/plain", status=status.HTTP_200_OK) # We use an HttpResponse to return the CRL as a text file
            else:
                return Response({'error': 'No CRL found for this event.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
