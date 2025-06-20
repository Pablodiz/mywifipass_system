from django import forms
from django_x509.models import Cert 
from getEAP_TLS.models import WifiUser

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Select CSV File", 
        help_text="Upload a CSV file with the following columns: name, email, id_document, wifiLocation",
    )


class WifiUserForm(forms.ModelForm):
    class Meta:
        model = WifiUser
        fields = ["name", "email", "id_document"]
