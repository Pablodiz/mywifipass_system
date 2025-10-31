# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

from django import forms
from mywifipass.models import WifiUser, WifiNetworkLocation

class CSVImportForm(forms.Form):
    wifiLocation = forms.ChoiceField(
        label="Select Wifi Location",
        choices= [("", "--SELECT A WIFI LOCATION--")],
    )

    csv_file = forms.FileField(
        label="Select CSV File", 
        help_text="Upload a CSV file with the following columns: name, email, id_document",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the choices for the wifiLocation field dynamically
        self.fields['wifiLocation'].choices += WifiNetworkLocation.objects.values_list('pk', 'name')


class WifiUserForm(forms.ModelForm):
    class Meta:
        model = WifiUser
        fields = ["name", "email", "id_document"]
