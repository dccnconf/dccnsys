from django.urls import path

from . import views


urlpatterns = [
    path('api/uploader/', views.uploader, name='uploader'),
]
