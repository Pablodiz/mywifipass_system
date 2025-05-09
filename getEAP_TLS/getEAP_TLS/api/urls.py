from django.urls import path
from . import rest_api 
from getEAP_TLS.settings import USER_PATH
from rest_framework.authtoken import views # Default function that provides a when username and password are provided


urlpatterns = [
    path(USER_PATH + "<uuid:uuid>/", rest_api.user, name='user-data'),
    path("user_qr/" + "<uuid:uuid>/", rest_api.user_qr, name='user-qr'),
    path(USER_PATH + "<uuid:uuid>/key", rest_api.user_key, name='user-key'),
    path('api-token-auth/', views.obtain_auth_token, name = 'api-token-auth'),
    path(USER_PATH + "<uuid:uuid>/authorize", rest_api.validate_user, name='authorize-user'),
    path(USER_PATH + "<uuid:user_uuid>/validate", rest_api.check_user, name='check-user'),
    path("events/<uuid:uuid>/crl", rest_api.show_crl, name='event-crl'),
]