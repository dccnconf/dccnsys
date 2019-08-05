from django.urls import path

from . import views


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
    path(
        '<int:conf_pk>/compose/user/<int:user_pk>/',
        views.compose_to_user,
        name='compose-user'
    ),
    path(
        '<int:conf_pk>/compose/paper/<int:sub_pk>/',
        views.compose_to_submission,
        name='compose-paper'
    ),
]
