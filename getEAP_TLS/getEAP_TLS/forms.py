from django import forms
from django_x509.models import Cert 
from getEAP_TLS.models import WifiUser

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="Select CSV File", 
                               help_text="Upload a CSV file with the following columns: name, email, id_document, wifiLocation",
                               )


class WifiUserForm(forms.ModelForm):
    CERTIFICATE_CHOICES = (
        ('-', '----- {0} -----'.format('Please select an option')),
        ('existing', 'Select an existing certificate'),
        ('new', 'Generate a new certificate'),
    )
    
    certificate_operation = forms.ChoiceField(
        choices=CERTIFICATE_CHOICES,
        label="Certificate Selection",
        help_text="Choose whether to select an existing certificate or generate a new one.",
        required=True,
    )

    class Meta:
        model = WifiUser
        fields = ["name", "email", "id_document", "wifiLocation", "certificate"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['certificate'].queryset = Cert.objects.all()
        self.fields['certificate'].required = False

