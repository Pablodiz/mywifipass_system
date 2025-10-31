# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django.urls import path, include
from . import auth, networks, users 
from mywifipass.settings import BASE_URL, API_PATH
from rest_framework.authtoken import views as authtoken_views # Default function that provides a when username and password are provided
import uuid
from mywifipass.models import WifiUser, WifiNetworkLocation
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from mywifipass.api.networks import WifiNetworkLocationViewSet
from mywifipass.api.users import WifiUserViewSet
from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter

NETWORK_PATH = "networks/<uuid:network_uuid>/"
USER_PATH = NETWORK_PATH + "users/<uuid:user_uuid>/"

schema_view = get_schema_view(
   openapi.Info(
      title="MyWifiPass API",
      default_version='v1',
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r'networks', WifiNetworkLocationViewSet, basename='network')

networks_router = NestedDefaultRouter(router, r'networks', lookup='network')
networks_router.register(r'users', WifiUserViewSet, basename='wifi-client')

urlpatterns = [
    path('', include(router.urls)),  # Include the networks URLs
    path('', include(networks_router.urls)),  # Include the users URLs
    path('login/password', authtoken_views.obtain_auth_token, name = 'api-password-auth'),
    path('login/token', auth.obtain_auth_token_username_token, name = 'api-token-auth'),
    path('swagger', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   ]

def base_url (user: WifiUser):
    """
    Function to get the URL of the user
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the user
    """
    return BASE_URL + API_PATH + f"networks/{str(user.wifiLocation.location_uuid)}/users/{str(user.user_uuid)}"

def wifipass_download_url (user: WifiUser):
    """
    Function to get the URL of the wifipass for an user
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the wifipass for an user
    """
    return base_url(user) + "/download/"

def user_qr_url (user: WifiUser):
    """
    Function to get the URL of the user QR code
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the user QR code
    """
    return base_url(user) + "/qr/"

def certificates_symmetric_key_url(user: WifiUser):
    """
    Function to get the URL of the symmetric key of the user
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the symmetric key of the user
    """
    return base_url(user) + "/key/"

def validation_url(user: WifiUser):
    """
    Function to get the URL for checking that the user exists for an event
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL for checking that the user exists for an event
    """
    return base_url(user) + "/validate/"

def authorize_url (user: WifiUser):
    """
    Function to get the URL for checking that the user exists for an event
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL where to authorize the user
    """
    return base_url(user) + "/authorize/"

def has_downloaded_url(user: WifiUser):
    """
    Function to get the URL for checking that the user has downloaded the pass
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL where to check if the user has downloaded the pass
    """
    return base_url(user) + "/downloaded/"

def certificates_url(user: WifiUser):
    """
    Function to get the URL for generating and obtaining the user certificates
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL for generating and obtaining the user certificates
    """
    return base_url(user) + "/certificates/"

def crl_url(network: WifiNetworkLocation):
    """
    Function to get the URL for the Certificate Revocation List (CRL) of a network
    Args:
        network: WifiNetworkLocation for whom the url is requested
    Returns:
        url: URL of the CRL of the network
    """
    return BASE_URL + API_PATH + f"networks/{str(network.location_uuid)}/crl/"

def email_url(user: WifiUser):
    """
    Function to get the URL that is sent to the user via email
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL sent in an email to the user
    """
    return "https://pablodiz.github.io/mywifipass?url=" + wifipass_download_url(user)

def check_user_authorized_url(user: WifiUser):
    """
    Function to get the URL for checking if the user is authorized
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL for checking if the user is authorized
    """
    return base_url(user) + "/check_user_authorized/"

def sign_certificate_url(user: WifiUser):
    """
    Function to get the URL for signing the user's certificate
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL for signing the user's certificate
    """
    return base_url(user) + "/sign_certificate/"