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
