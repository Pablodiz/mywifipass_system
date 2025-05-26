from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from mywifipass.api.auth_model import User, LoginToken

@api_view(['POST'])
def obtain_auth_token_username_token(request):
    """
    Handles the HTTP request to obtain a HTTP authentication token from a username and token.
    
    Args:
        request: The HTTP request object.
    
    Returns:
        Response: A response containing the authentication token or an error message.
    """
    try:
        username = request.data.get('username')
        qr_token = request.data.get('token')
        if not username or not qr_token:
            return Response({'error': 'username and token are required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = get_object_or_404(User, username=username)
        except Http404:
            return Response({'error': f'User with username {username} not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            token = get_object_or_404(LoginToken, token=qr_token, user=user)
            if token.is_valid():
                auth_token, created = Token.objects.get_or_create(user=user)
                return Response({'token': str(auth_token)}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Token is expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except Http404:
            return Response({'error': f'Token {qr_token} not found for user {username}.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    