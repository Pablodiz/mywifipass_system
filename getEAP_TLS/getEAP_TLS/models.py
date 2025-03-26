from django.db import models

from django_x509.models import Cert, Ca


class WifiUser(models.Model):
    """
    Wifi user model
    """

    id_document = models.CharField(max_length=20, blank=False, null=False)
    certificate = models.ForeignKey(Cert, on_delete=models.SET_NULL, blank=False, null=True)
    wifiLocation = models.ForeignKey('WifiNetworkLocation', on_delete=models.SET_NULL, blank=False, null=True)
    uuid = models.UUIDField(default=None, blank=True, null=True) 
    @property
    def name(self):
        return self.certificate.name
    
    @property 
    def email(self):
        return self.certificate.email
    
    def __str__(self):
        return self.name


class WifiNetworkLocation(models.Model):
    """
    Model that represents the event/organization where the wifi network is located at
    """

    name = models.CharField(max_length=64, blank=False, null=False)
    certificates_CA = models.ForeignKey(Ca, on_delete=models.SET_NULL, blank=False, null=True, related_name="certificates_CA")
    radius_CA = models.ForeignKey(Ca, on_delete=models.SET_NULL, blank=False, null=True, related_name="radius_CA")
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=64, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    SSID = models.CharField(max_length=32, blank=False, null=True)
    def __str__(self):
        return self.name