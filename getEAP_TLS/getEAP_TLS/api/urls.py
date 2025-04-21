from django.urls import path
from . import rest_api 
from getEAP_TLS.settings import USER_PATH


urlpatterns = [
    path(USER_PATH + "<uuid:uuid>/", rest_api.user, name='user-data'),
    path("user_qr/" + "<uuid:uuid>/", rest_api.user_qr, name='user-qr'),
    path(USER_PATH + "<uuid:uuid>/key", rest_api.user_key, name='user-key'),
]