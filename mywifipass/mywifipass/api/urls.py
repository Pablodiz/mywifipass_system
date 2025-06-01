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
from rest_framework.routers import DefaultRouter

NETWORK_PATH = "events/<uuid:network_uuid>/"
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

urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs
    path('login/password', authtoken_views.obtain_auth_token, name = 'api-password-auth'),
    path('login/token', auth.obtain_auth_token_username_token, name = 'api-token-auth'),
    path(USER_PATH, users.user, name='user-data'),
    path(USER_PATH + "qr", users.user_qr, name='user-qr'),
    path(USER_PATH + "authorize", users.allow_access_to_user, name='authorize-user'),
    path(USER_PATH + "validate", users.check_user, name='check-user'),
    path(USER_PATH + "downloaded", users.has_downloaded_pass, name='downloaded'),
    path(USER_PATH + "certificates", users.generate_certificates, name='generate-certificates'),
    path('swagger', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   ]

def user_url (user: WifiUser):
    """
    Function to get the URL of the user
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the user
    """
    return BASE_URL + API_PATH + f"events/{str(user.wifiLocation.location_uuid)}/users/{str(user.user_uuid)}"

def user_qr_url (user: WifiUser):
    """
    Function to get the URL of the user QR code
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the user QR code
    """
    return user_url(user) + "/qr"

def certificates_symmetric_key_url(user: WifiUser):
    """
    Function to get the URL of the symmetric key of the user
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL of the symmetric key of the user
    """
    return user_url(user) + "/key"

def validation_url(user: WifiUser):
    """
    Function to get the URL for checking that the user exists for an event
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL for checking that the user exists for an event
    """
    return user_url(user) + "/validate"

def authorize_url (user: WifiUser):
    """
    Function to get the URL for checking that the user exists for an event
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL where to authorize the user
    """
    return user_url(user) + "/authorize"

def has_downloaded_url(user: WifiUser):
    """
    Function to get the URL for checking that the user has downloaded the pass
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL where to check if the user has downloaded the pass
    """
    return user_url(user) + "/downloaded"

def certificates_url(user: WifiUser):
    """
    Function to get the URL for generating and obtaining the user certificates
    Args:
        user: WifiUser for whom the url is requested
    Returns:
        url: URL for generating and obtaining the user certificates
    """
    return user_url(user) + "/certificates"