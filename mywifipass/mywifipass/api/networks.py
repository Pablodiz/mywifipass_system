from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import uuid 
from django.http import HttpResponse
from mywifipass.models import WifiNetworkLocation

@api_view(['GET'])
def show_crl(request, network_uuid:uuid):
    """
    Handles the HTTP request to show the Certificate Revocation List (CRL) of an event.
    
    Args:
        request: The HTTP request object.
    
    Returns:
        Response: A response containing the CRL or an error message.
    """
    try:
        event = get_object_or_404(WifiNetworkLocation, location_uuid=network_uuid)
        crl = event.certificates_CA.crl
        if crl:
            crl_text = crl.decode('utf-8')
            print(crl_text)
            return HttpResponse(crl_text, content_type="text/plain", status=status.HTTP_200_OK) # We use an HttpResponse to return the CRL as a text file
        else:
            return Response({'error': 'No CRL found for this event.'}, status=status.HTTP_404_NOT_FOUND)
    except Http404:
        return Response({'error': 'Event with UUID ' + str(network_uuid) + ' not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    