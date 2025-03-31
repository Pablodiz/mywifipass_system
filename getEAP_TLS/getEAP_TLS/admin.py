from getEAP_TLS.models import WifiUser, WifiNetworkLocation
from django.contrib.admin import ModelAdmin
from django.contrib import admin as django_admin
from django_x509.models import Cert, Ca

class WifiUserAdmin(ModelAdmin):
    """
    Admin class for a WifiUser model
    """
    list_display = ["name", "email", "id_document", "wifiLocation"]
    search_fields = ["name", "email","id_document"] 
    fields = ["name", "email","id_document", "wifiLocation"]
    list_filter = ["wifiLocation"]


class WifiNetworkLocationAdmin(ModelAdmin):
    """
    Admin class for a WifiLocation model
    """
    list_display = ["name",  "SSID", "location", "start_date", "end_date"]
    search_fields = ["name", "SSID", "description", "location"]
    fields = ["name", "SSID", "description", "location", "start_date", "end_date"]
    

django_admin.site.register(WifiUser, WifiUserAdmin)
django_admin.site.register(WifiNetworkLocation, WifiNetworkLocationAdmin)
# Unregister Ca and Cert from admin panel "para que sea transparente para el usuario" 
django_admin.site.unregister(Cert)
django_admin.site.unregister(Ca)

django_admin.site.site_header = "getEAP_TLS Administration"
django_admin.site.site_title = "getEAP_TLS site Administration"
django_admin.site.index_title = "getEAP_TLS Administration"
