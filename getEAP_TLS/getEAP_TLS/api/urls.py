from django.urls import path


from . import rest_api 

urlpatterns = [
    path('user/<uuid:uuid>/', rest_api.user, name='user-data'),
]