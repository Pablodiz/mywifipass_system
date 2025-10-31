# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

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
    path('', RedirectView.as_view(url='/networks/', permanent=False)),
    path('admin/qr/', admin_qr_view, name='admin_qr_view'),
    path('admin/', admin.site.urls),
    path(API_PATH, include('mywifipass.api.urls')),
    path('networks/', view=mywifipass.views.wifi_network_locations_list, name="networks"),
    path('networks/<uuid:location_uuid>/', view=mywifipass.views.wifi_location_details, name="wifi_location_details"),
    path('networks/<uuid:location_uuid>/register', view=mywifipass.views.wifi_user_autoregistration, name="wifi_user_autoregistration"),
    path('networks/<uuid:location_uuid>/confirmation', view=mywifipass.views.wifi_user_registration_done, name="register_confirmation"),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
