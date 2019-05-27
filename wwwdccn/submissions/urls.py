from django.urls import path

from . import views


app_name = 'submissions'


urlpatterns = [
    path('create/', views.create_submission, name='create'),
    path('<int:pk>/details/', views.submission_details, name='details'),
    path('<int:pk>/authors/', views.submission_authors, name='authors'),
    path('<int:pk>/manuscript/', views.edit_manuscript, name='edit-manuscript'),
    path('<int:pk>/manuscript/delete/', views.delete_manuscript,
         name='delete-manuscript'),
    path('<int:pk>/manuscript/download/', views.download_manuscript,
         name='download-manuscript'),
    path('<int:pk>', views.submission_overview, name='overview'),
    path('<int:pk>/delete/', views.submission_delete, name='delete'),

    path('<int:pk>/authors/delete/', views.delete_author, name='delete-author'),
    path('<int:pk>/authors/create/', views.create_author, name='create-author'),
    path('<int:pk>/authors/order/', views.order_authors, name='order-authors'),
    path('<int:pk>/authors/invite/', views.send_invitation, name='invite'),
]
