from django.contrib.admin import ModelAdmin
from django.contrib import admin as django_admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import path
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render

from getEAP_TLS.radius.radius_certs import export_wifi_location_certificates
from django_x509.models import Cert, Ca
from getEAP_TLS.models import WifiUser, WifiNetworkLocation

from getEAP_TLS.forms import CSVImportForm
import csv
from io import TextIOWrapper
from django.http import HttpResponseRedirect

class WifiUserAdmin(ModelAdmin):
    """
    Admin class for a WifiUser model
    """
    list_display = ["name", "email", "id_document", "wifiLocation", "user_uuid"]
    search_fields = ["name", "email","id_document"] 
    fields = ["name", "email","id_document", "wifiLocation"]
    list_filter = ["wifiLocation"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import_csv/', self.admin_site.admin_view(self.import_csv), name="import_wifi_users"),
        ]
        return custom_urls + urls

    
    def import_csv(self, request):
        if request.method == "POST":
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
                reader = csv.DictReader(csv_file)
                errors = []
                success_count = 0

                for row in reader:
                    try:
                        wifi_location = WifiNetworkLocation.objects.get(name=row['wifiLocation'])
                        WifiUser.objects.create(
                            name=row['name'],
                            email=row['email'],
                            id_document=row['id_document'],
                            wifiLocation=wifi_location
                        )
                        success_count += 1
                    except WifiNetworkLocation.DoesNotExist:
                        errors.append(f"WifiLocation '{row['wifiLocation']}' not found for user '{row['name']}'.")
                    except Exception as e:
                        errors.append(f"Error processing user '{row['name']}': {e}")

                if success_count > 0:
                    self.message_user(request, f"Successfully imported {success_count} users.")
                if errors:
                    self.message_user(request, f"Errors occurred: {'; '.join(errors)}", level="error")
                return HttpResponseRedirect("../")

        form = CSVImportForm()
        context = {
            'form': form,
            'title': "Import WifiUsers from CSV",
        }
        return render(request, "admin/csv_form.html", context)
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['custom_button'] = {
            'url': 'import_csv/',
        }
        return super().changelist_view(request, extra_context=extra_context)
class WifiNetworkLocationAdmin(ModelAdmin):
    """
    Admin class for a WifiNetworkLocation model
    """
    list_display = ["name", "SSID", "location", "start_date", "end_date", "export_certificates_button"]
    search_fields = ["name", "SSID", "description", "location"]
    fields = ["name", "SSID", "description", "location", "start_date", "end_date"]

    def export_certificates_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Export Certificates</a>',
            f"export_certificates/{obj.id}/"
        )

    export_certificates_button.short_description = "Export Certificates"
    export_certificates_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export_certificates/<int:wifi_location_id>/', self.admin_site.admin_view(self.export_certificates), name="export_wifi_certificates"),
        ]
        return custom_urls + urls

    def export_certificates(self, request, wifi_location_id):
        try:
            export_wifi_location_certificates(wifi_location_id)
            self.message_user(request, "Certificates exported successfully.")
        except ObjectDoesNotExist:
            self.message_user(request, "Wifi location not found.", level="error")
        except Exception as e:
            self.message_user(request, f"Error: {e}", level="error")
        return redirect(request.META.get('HTTP_REFERER', 'admin:index'))

    




django_admin.site.register(WifiUser, WifiUserAdmin)
django_admin.site.register(WifiNetworkLocation, WifiNetworkLocationAdmin)
# Unregister Ca and Cert from admin panel "para que sea transparente para el usuario" 
django_admin.site.unregister(Cert)
django_admin.site.unregister(Ca)

django_admin.site.site_header = "getEAP_TLS Administration"
django_admin.site.site_title = "getEAP_TLS site Administration"
django_admin.site.index_title = "getEAP_TLS Administration"
