from django.urls import path

from . import views


urlpatterns = [
    path('ajax/<int:pk>/', views.ajax_conference_details, name='ajax-conference-details'),
    path('ajax/stype/<int:pk>/', views.ajax_submission_type_details, name='ajax-submission-type-details'),
]
