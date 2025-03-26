#from django_x509 import admin # noqa
from getEAP_TLS.models import WifiUser, WifiNetworkLocation
from django.contrib.admin import ModelAdmin
from django.contrib import admin as django_admin



# Para que salga en la interfaz de admin, se crea una clase que hereda de ModelAdmin
# y se registra en el admin de django
class WifiUserAdmin(ModelAdmin):
    """
    Admin class for a WifiUser model
    """
    list_display = ["name", "email", "id_document", "certificate", "wifiLocation", "get_name"]
    search_fields = ["id_document"] 
    fields = ["id_document", "certificate", "wifiLocation"]


class WifiNetworkLocationAdmin(ModelAdmin):
    """
    Admin class for a WifiLocation model
    """
    # Campos que se mostrarán en la lista de ubicaciones
    list_display = ["name", "radius_CA", "certificates_CA", "description", "location", "start_date", "end_date", "SSID"]
    # Campos con los que se podrán buscar ubicaciones
    search_fields = ["name", "description", "location", "start_date", "end_date"]
    # Campos editables en la interfaz de admin
    fields = ["name", "radius_CA", "certificates_CA", "description", "location", "start_date", "end_date", "SSID"]
    

django_admin.site.register(WifiUser, WifiUserAdmin)
django_admin.site.register(WifiNetworkLocation, WifiNetworkLocationAdmin)


