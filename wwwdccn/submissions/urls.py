from django.urls import path

from . import views


urlpatterns = [
    path('create/', views.create_submission, name='submission-create'),
    path('<int:pk>/details/', views.submission_details, name='submission-details'),
    path('<int:pk>/authors/', views.submission_authors, name='submission-authors'),
    path('<int:pk>/manuscript/', views.submission_manuscript, name='submission-manuscript'),
    path('<int:pk>', views.submission_overview, name='submission-overview'),
    path('<int:pk>/delete/', views.submission_delete, name='submission-delete'),

    path('<int:pk>/authors/delete/',
         views.submission_author_delete,
         name='submission-author-delete'),
    path('<int:pk>/authors/create/',
         views.submission_author_create,
         name='submission-author-create'),
    path('<int:pk>/authors/reorder/',
         views.submission_authors_reorder,
         name='submission-authors-reorder'),
]
