from django.urls import path

from . import views


urlpatterns = [
    path('create/', views.create_submission, name='submission-create'),
    path('<int:pk>/details/', views.submission_details, name='submission-details'),
    path('<int:pk>/authors/', views.submission_authors, name='submission-authors'),
    path('<int:pk>/manuscript/', views.submission_manuscript, name='submission-manuscript'),
    path('<int:pk>', views.submission_overview, name='submission-overview'),
]
