from django.urls import path

from . import views


app_name = 'user_site'

urlpatterns = [
    path('submissions/', views.submissions, name='submissions'),
    path('reviews/', views.reviews, name='reviews'),
]
