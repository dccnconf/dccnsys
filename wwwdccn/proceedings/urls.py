from django.urls import path

from proceedings import views

app_name = 'proceedings'

urlpatterns = [
    path('api/camera_ready/<int:camera_id>/update_volume/', views.update_volume, name='update-volume'),
]
