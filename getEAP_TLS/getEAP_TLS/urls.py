from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from getEAP_TLS.settings import API_PATH
import getEAP_TLS.views
import uuid 

urlpatterns = [
    path('', RedirectView.as_view(url='/events/', permanent=False)),
    path('admin/', admin.site.urls),
    path(API_PATH, include('getEAP_TLS.api.urls')),
    path('events/', view=getEAP_TLS.views.wifi_network_locations_list, name="events"),
    path('events/<uuid:location_uuid>/', view=getEAP_TLS.views.wifi_location_details, name="wifi_location_details"),
    path('events/<uuid:location_uuid>/register', view=getEAP_TLS.views.wifi_user_autoregistration, name="wifi_user_autoregistration"),
]