from django.contrib.admin import ModelAdmin
from django.contrib import admin as django_admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import path
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render, get_object_or_404

#from getEAP_TLS.radius.radius_certs import export_wifi_location_certificates
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
    list_display = ["name", "email", "id_document", "wifiLocation", "show_qr_button", "allow_access", "revoke_certificate_button"]
    search_fields = ["name", "email","id_document"] 
    fields = ["name", "email","id_document", "wifiLocation", "allow_access"]
    list_filter = ["wifiLocation"]
    list_editable = ["allow_access"]

    def show_qr_button(self, obj:WifiUser):
        return format_html(
            '<a class="button" style="display: inline-block;text-align: center" href="{}">Show QR</a>',
            f"/api/user_qr/{obj.user_uuid}/"
        )
    
    def revoke_certificate_button(self, obj: WifiUser):
        if obj.certificate: 
            if obj.certificate.revoked:
                return format_html(
                    '<a class="button" style="display: inline-block;text-align: center" disabled>Certificate revoked</button>'
                )
            else:
                url = f"/admin/getEAP_TLS/wifiuser/{obj.user_uuid}/revoke_certificate/"
                return format_html(
                    '<a class="button" style="display: inline-block;text-align: center" href="{}">Revoke Certificate</a>',
                    url
                )
        else: 
            return format_html('<a class="button" style="display: inline-block;text-align: center" disabled>No Certificate</button>')


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import_csv/', self.admin_site.admin_view(self.import_csv), name="import_wifi_users"),
            path('<uuid:uuid>/revoke_certificate/',self.admin_site.admin_view(self.revoke_certificate_view), name='revoke-certificate')            
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


    revoke_certificate_button.short_description = "Revoke Certificate"

    def revoke_certificate_view(self, request, uuid):
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        try:
            user.revoke_certificate()
            print("done donete")
            self.message_user(request, f"Certificate for user '{user.name}' has been revoked.", messages.SUCCESS)
        except ValueError as e:
            self.message_user(request, str(e), messages.ERROR)
        return redirect(f"/admin/getEAP_TLS/wifiuser/")       
    
class WifiNetworkLocationAdmin(ModelAdmin):
    """
    Admin class for a WifiNetworkLocation model
    """
    list_display = ["name", "SSID", "location", "start_date", "end_date"]
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
