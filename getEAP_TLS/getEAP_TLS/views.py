from getEAP_TLS.models import WifiNetworkLocation
from getEAP_TLS.forms import WifiUserForm 
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from getEAP_TLS.utils import generate_qr_code
from getEAP_TLS.api.auth_model import LoginToken
from django.utils import timezone
from datetime import timedelta
from getEAP_TLS.settings import BASE_URL

def wifi_network_locations_list(request):
    locations = WifiNetworkLocation.objects.all()
    return render(request, "getEAP_TLS/wifilocation/wifi_network_locations_list.html", {"locations": locations})


def wifi_location_details(request, location_uuid):
    """View for displaying the details of a specific WifiNetworkLocation."""
    event = get_object_or_404(WifiNetworkLocation, location_uuid=location_uuid)
    return render(request, "getEAP_TLS/wifilocation/wifi_location_details.html", {"location": event})


def wifi_user_autoregistration(request, location_uuid):
    # Get the event object using the location_uuid        
    event = get_object_or_404(WifiNetworkLocation, location_uuid=location_uuid)
    if request.method == "POST":
        form = WifiUserForm(request.POST)
        if form.is_valid():
            wifi_user = form.save(commit=False)
            # Set the wifiLocation field to the event
            wifi_user.wifiLocation = event
            wifi_user = form.save()
            return HttpResponseRedirect("../")
    else:
        form = WifiUserForm()

    return render(request, "getEAP_TLS/wifiuser/register.html", {"form": form, "event": event})

def admin_qr_view(request):
    LoginToken.objects.filter(expires_at__lt=timezone.now()).delete()
    token = LoginToken.objects.create(
        user=request.user,
        expires_at=timezone.now() + timedelta(minutes=5)
    )
    data = {
        "username": request.user.username,
        "token": str(token.token),
        "url": BASE_URL + "api/login/token"
    }
    qr_img = generate_qr_code(data)  
    return HttpResponse(qr_img, content_type='image/png')   