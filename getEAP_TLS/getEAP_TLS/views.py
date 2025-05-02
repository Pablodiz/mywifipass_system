from getEAP_TLS.models import WifiNetworkLocation
from getEAP_TLS.forms import WifiUserForm 
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404

def wifi_network_locations_list(request):
    locations = WifiNetworkLocation.objects.all()
    return render(request, "getEAP_TLS/wifilocation/wifi_network_locations_list.html", {"locations": locations})


def wifi_location_details(request, event_id):
    """View for displaying the details of a specific WifiNetworkLocation."""
    event = get_object_or_404(WifiNetworkLocation, id=event_id)
    return render(request, "getEAP_TLS/wifilocation/wifi_location_details.html", {"location": event})


def wifi_user_autoregistration(request, event_id):
    # Get the event object using the event_id        
    event = get_object_or_404(WifiNetworkLocation, id=event_id)
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
