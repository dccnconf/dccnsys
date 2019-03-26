from django.urls import path

from . import views


urlpatterns = [
    path('', views.user_details, name='user-details'),
]
