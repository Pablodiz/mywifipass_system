from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from getEAP_TLS.settings import API_PATH


urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=True)),
    path('admin/', admin.site.urls),
    path(API_PATH, include('getEAP_TLS.api.urls')),
]
