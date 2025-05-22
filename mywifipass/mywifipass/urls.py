from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from mywifipass.settings import API_PATH
import mywifipass.views
import uuid 
from mywifipass.views import admin_qr_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', RedirectView.as_view(url='/events/', permanent=False)),
    path('admin/qr/', admin_qr_view, name='admin_qr_view'),
    path('admin/', admin.site.urls),
    path(API_PATH, include('mywifipass.api.urls')),
    path('events/', view=mywifipass.views.wifi_network_locations_list, name="events"),
    path('events/<uuid:location_uuid>/', view=mywifipass.views.wifi_location_details, name="wifi_location_details"),
    path('events/<uuid:location_uuid>/register', view=mywifipass.views.wifi_user_autoregistration, name="wifi_user_autoregistration"),
    path('events/<uuid:location_uuid>/confirmation', view=mywifipass.views.wifi_user_registration_done, name="register_confirmation"),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
