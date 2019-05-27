from django.urls import path

from . import views


app_name = 'user_site'

urlpatterns = [
    path('', views.submissions, name='submissions'),
]
