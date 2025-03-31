from django.urls import path


from . import rest_api 

urlpatterns = [
    path('user/', rest_api.user),
]