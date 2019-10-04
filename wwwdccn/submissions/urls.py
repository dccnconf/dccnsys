from django.urls import path

from . import views


app_name = 'submissions'


urlpatterns = [
    path('create/', views.create_submission, name='create'),
    path('create/<int:pk>/', views.create_submission_for, name='create-for'),
    path('<int:pk>/details/', views.submission_details, name='details'),
    path('<int:pk>/authors/', views.submission_authors, name='authors'),
    path('<int:pk>/manuscript/', views.edit_manuscript, name='edit-manuscript'),
    path('<int:pk>/manuscript/delete/', views.delete_manuscript, name='delete-manuscript'),
    path('<int:pk>/manuscript/download/', views.download_manuscript, name='download-manuscript'),
    path('<int:pk>', views.submission_overview, name='overview'),
    path('<int:pk>/delete/', views.submission_delete, name='delete'),
    path('<int:pk>/camera_ready/', views.camera_ready, name='camera-ready'),
    path('<int:pk>/attachments/<int:att_pk>/upload/', views.upload_attachment, name='upload-attachment'),
    path('<int:pk>/attachments/<int:att_pk>/download/', views.download_attachment, name='download-attachment'),
    path('<int:pk>/attachments/<int:att_pk>/delete/', views.delete_attachment, name='delete-attachment'),

    path('<int:pk>/authors/delete/', views.delete_author, name='delete-author'),
    path('<int:pk>/authors/create/', views.create_author, name='create-author'),
    path('<int:pk>/authors/order/', views.order_authors, name='order-authors'),
    path('<int:pk>/authors/invite/', views.send_invitation, name='invite'),

    path('<int:pk>/update_status/', views.update_status, name='update-status'),
]
