from django.urls import path
from . import rest_api 
from getEAP_TLS.settings import BASE_URL, API_PATH, USER_PATH
from rest_framework.authtoken import views as authtoken_views # Default function that provides a when username and password are provided
import uuid

urlpatterns = [
    path(USER_PATH + "<uuid:uuid>/", rest_api.user, name='user-data'),
    path("user_qr/" + "<uuid:uuid>/", rest_api.user_qr, name='user-qr'),
    path(USER_PATH + "<uuid:uuid>/key", rest_api.user_key, name='user-key'),
    path('login/password', authtoken_views.obtain_auth_token, name = 'api-password-auth'),
    path('login/token', rest_api.obtain_auth_token_username_token, name = 'api-token-auth'),
    path(USER_PATH + "<uuid:uuid>/authorize", rest_api.allow_access_to_user, name='authorize-user'),
    path(USER_PATH + "<uuid:user_uuid>/validate", rest_api.check_user, name='check-user'),
    path(USER_PATH + "<uuid:user_uuid>/downloaded", rest_api.has_downloaded_pass, name='downloaded'),
    path("events/<uuid:uuid>/crl", rest_api.show_crl, name='event-crl'),
]

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
    Function to get the URL for checking that the user exists for an event
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL for checking that the user exists for an event
    """
    return user_url(user_uuid) + "/validate"

def authorize_url (user_uuid: uuid):
    """
    Function to get the URL for checking that the user exists for an event
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL where to authorize the user
    """
    return user_url(user_uuid) + "/authorize"

def has_downloaded_url(user_uuid: uuid):
    """
    Function to get the URL for checking that the user has downloaded the pass
    Args:
        user_uuid: UUID of the user
    Returns:
        url: URL where to check if the user has downloaded the pass
    """
    return user_url(user_uuid) + "/downloaded"