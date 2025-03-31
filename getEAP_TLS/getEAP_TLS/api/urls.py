from django.urls import path


from . import rest_api 

urlpatterns = [
    path('user/<int:id>/', rest_api.user, name='user-data'),
]