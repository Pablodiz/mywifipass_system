from django.contrib.admin import ModelAdmin
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect, render, get_object_or_404, reverse

from django_x509.models import Cert, Ca
from mywifipass.models import WifiUser, WifiNetworkLocation
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import TokenProxy
from django.contrib.admin.sites import NotRegistered

from mywifipass.forms import CSVImportForm
import csv
from io import TextIOWrapper
from django.http import HttpResponseRedirect
from mywifipass.api.urls import user_qr_url


button_style = "display: inline-block; text-align: center; width: 120px; padding: 8px 12px; box-sizing: border-box;"

class WifiUserAdmin(ModelAdmin):
    """
    Admin class for a WifiUser model
    """
    list_display = ["name", "email", "id_document", "wifiLocation", "has_downloaded_pass", "has_attended", "revoke_certificate_button", "show_qr_button"]
    search_fields = ["name", "email","id_document"] 
    fields = ["name", "email","id_document", "wifiLocation"]
    list_filter = ["wifiLocation"]
    list_editable = ["has_downloaded_pass", "has_attended"]

    def has_change_permission(self, request, obj=None):
        if obj and obj.certificate and obj.certificate.revoked:
            if not hasattr(request, '_revoked_message_shown'):
                self.message_user(request, "Certificate is revoked. Cannot change user.", level=messages.ERROR)
                request._revoked_message_shown = True
            return False
        return super().has_change_permission(request, obj)
    
    def show_qr_button(self, obj:WifiUser):
        url = user_qr_url(obj)
        return format_html(
            '<a class="button" style="{}" href="{}">Show QR</a>',
            button_style, url
        )
    
    def revoke_certificate_button(self, obj: WifiUser):
        if obj.certificate: 
            if obj.certificate.revoked:
                return format_html(
                    '<span class="button" style="{}" disabled>Certificate revoked</span>',
                    button_style
                )
            else:
                url = f"/admin/mywifipass/wifiuser/{obj.user_uuid}/revoke_certificate/"
                return format_html(
                    '<a class="button" style="{}" href="{}">Revoke Certificate</a>',
                    button_style,
                    url
                )
        else: 
            return format_html(
                '<span class="button" style="{}" disabled>No Certificate</span>',
                button_style
            )
    
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
                try:
                    csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
                    reader = csv.DictReader(csv_file)
                    errors = []
                    success_count = 0

                    for row in reader:
                        try:
                            selected_wifi_location = form.cleaned_data['wifiLocation']
                            wifi_location = WifiNetworkLocation.objects.get(pk=selected_wifi_location)
                            user = WifiUser(
                                name=row['name'],
                                email=row['email'],
                                id_document=row['id_document'],
                                wifiLocation=wifi_location
                            )
                            user.save()
                            success_count += 1
                        
                        except Exception as e:
                            errors.append(f"Error processing user '{row['name']}': {e}")

                    if success_count > 0:
                        self.message_user(request, f"Successfully imported {success_count} users.")
                    if errors:
                        self.message_user(request, f"Errors occurred: {'; '.join(errors)}", level="error")
                    
                    return HttpResponseRedirect(reverse('admin:mywifipass_wifiuser_changelist'))
                
                except Exception as e:
                    self.message_user(request, f"An error occurred while processing the CSV file", level="error")
        else:
            form = CSVImportForm()
        
        context = self.admin_site.each_context(request)
        context['form'] = form
        context['title'] = "Import WifiUsers from CSV"

        return render(request, "admin/csv_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['custom_button'] = {
            'url': 'import_csv/',
        }
        return super().changelist_view(request, extra_context=extra_context)


    revoke_certificate_button.short_description = "Revoke Certificate"
    show_qr_button.short_description = "Show QR Code"

    def revoke_certificate_view(self, request, uuid):
        user = get_object_or_404(WifiUser, user_uuid=uuid)
        try:
            user.revoke_certificate()
            self.message_user(request, f"Certificate for user '{user.name}' has been revoked.", messages.SUCCESS)
        except ValueError as e:
            self.message_user(request, str(e), messages.ERROR)
        return redirect(f"/admin/mywifipass/wifiuser/")       
    
class WifiNetworkLocationAdmin(ModelAdmin):
    """
    Admin class for a WifiNetworkLocation model
    """
    list_display = ["name", "SSID", "location", "start_date", "end_date", "is_enabled_in_radius", "is_visible_in_web", "requires_validator"]
    search_fields = ["name", "SSID", "description", "location"]
    fields = ["name", "SSID", "brief_description", "description", "location", "start_date", "end_date", "logo", "form_link", "is_registration_open", "is_enabled_in_radius", "is_visible_in_web", "requires_validator"]


admin.site.register(WifiUser, WifiUserAdmin)
admin.site.register(WifiNetworkLocation, WifiNetworkLocationAdmin)
# Unregister unnecesary classes from admin panel
admin.site.unregister(Cert)
admin.site.unregister(Ca)
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(TokenProxy)

admin.site.site_header = "MyWifiPass Administration"
admin.site.site_title = "MyWifiPass site Administration"
admin.site.index_title = "MyWifiPass Administration"



