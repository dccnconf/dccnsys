from django.urls import path

from . import views


app_name = 'review'

urlpatterns = [
    path('<int:pk>/', views.review_details, name='review-details'),
]