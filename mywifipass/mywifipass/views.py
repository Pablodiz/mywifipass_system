# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from mywifipass.models import WifiNetworkLocation
from mywifipass.forms import WifiUserForm 
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from mywifipass.utils import generate_qr_code
from mywifipass.api.auth_model import LoginToken
from django.utils import timezone
from datetime import timedelta
from mywifipass.settings import BASE_URL
import json 

def wifi_network_locations_list(request):
    locations = WifiNetworkLocation.objects.all()
    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Active networks", "url": "/networks/"},
    ]

    return render(request, "mywifipass/wifilocation/wifi_network_locations_list.html", {"locations": locations, "breadcrumbs": breadcrumbs})


def wifi_location_details(request, location_uuid):
    """View for displaying the details of a specific WifiNetworkLocation."""
    network = get_object_or_404(WifiNetworkLocation, location_uuid=location_uuid)
    
    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Active networks", "url": "/networks/"},
        {"name": network.name, "url": f"/networks/{location_uuid}/"},
    ]
    return render(request, "mywifipass/wifilocation/wifi_location_details.html", {"location": network, "breadcrumbs": breadcrumbs})


def wifi_user_autoregistration(request, location_uuid):
    # Get the network object using the location_uuid        
    network = get_object_or_404(WifiNetworkLocation, location_uuid=location_uuid)
    if request.method == "POST":
        form = WifiUserForm(request.POST)
        if form.is_valid():
            wifi_user = form.save(commit=False)
            # Set the wifiLocation field to the network
            wifi_user.wifiLocation = network
            wifi_user = form.save()
            return redirect('register_confirmation', location_uuid=network.location_uuid)
    else:
        form = WifiUserForm()

    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Active networks", "url": "/networks/"},
        {"name": network.name, "url": f"/networks/{location_uuid}/"},
        {"name": "Registration", "url": f"/networks/{location_uuid}/register"},
    ]
        
    return render(request, "mywifipass/wifiuser/register.html", {"form": form, "location": network, "breadcrumbs": breadcrumbs})

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
    json_data = json.dumps(data) 
    qr_img = generate_qr_code(str(json_data))  
    return HttpResponse(qr_img, content_type='image/png')   


def wifi_user_registration_done(request, location_uuid):
    """View for displaying the registration done page."""
    network = get_object_or_404(WifiNetworkLocation, location_uuid=location_uuid)
    
    breadcrumbs = [
        {"name": "Home", "url": "/"},
        {"name": "Active networks", "url": "/networks/"},
        {"name": "Registration confirm", "url": f"/networks/{location_uuid}/confirmation"}
    ]
    
    return render(request, "mywifipass/wifiuser/confirmation.html", {"location": network, "breadcrumbs": breadcrumbs})