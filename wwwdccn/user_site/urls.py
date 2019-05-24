from django.urls import path

from .views import submissions


urlpatterns = [
    path('', submissions.user_details, name='submissions'),
]
