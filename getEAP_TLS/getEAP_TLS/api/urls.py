from django.urls import path


from . import rest_api 

urlpatterns = [
    path('hello/', rest_api.hello),
    path('user/', rest_api.user),
]