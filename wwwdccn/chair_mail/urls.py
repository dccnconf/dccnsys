from django.urls import path

from chair_mail import forms
from . import views, api


app_name = 'chair_mail'

urlpatterns = [
    path('<int:conf_pk>/overview/', views.overview, name='overview'),
    path('<int:conf_pk>/frame/', views.frame_details, name='frame-details'),
    path(
        '<int:conf_pk>/frame/create/',
        views.create_frame,
        name='create-frame'
    ),
    path(
        '<int:conf_pk>/frame/send_test_message/',
        views.send_frame_test_message,
        name='send-frame-test'
    ),
    path(
        '<int:conf_pk>/messages/',
        views.sent_messages,
        name='sent-messages'
    ),
    path(
        '<int:conf_pk>/messages/<int:msg_pk>/',
        views.group_message_details,
        name='message-details'
    ),
    path(
        '<int:conf_pk>/messages/instance/<int:msg_pk>/',
        views.message_details,
        name='instance-details'
    ),
    path('<int:conf_pk>/compose/user/', views.compose_user, name='compose-user'),
    path('<int:conf_pk>/compose/submission/', views.compose_submission, name='compose-submission'),
    path('help/compose/', views.help_compose, name='help-compose'),

    #########################################################################
    path('<int:conf_pk>/api/mailing_lists/', api.list_mailing_lists, name='list-mailing-lists'),
    path('<int:conf_pk>/api/mailing_lists/<str:name>/', api.mailing_list_details, name='mailing-list-details'),
    path('<int:conf_pk>/api/users/', api.list_users, name='list-users'),
    path('<int:conf_pk>/api/submissions/', api.list_submissions, name='list-submissions'),
    path(
        '<int:conf_pk>/api/preview/user/',
        api.create_preview_view(forms.PreviewUserMessageForm),
        name='render-preview-user'),
    path(
        '<int:conf_pk>/api/preview/submission/',
        api.create_preview_view(forms.PreviewSubmissionMessageForm),
        name='render-preview-submission'),
]
