from django.urls import path

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
    path(
        '<int:conf_pk>/compose/paper/<int:sub_pk>/',
        views.compose_to_submission,
        name='compose-paper'
    ),
    path(
        '<int:conf_pk>/api/compose/preview/submission/<int:sub_pk>/',
        views.render_submission_message_preview,
        name='api-render-preview-submission',
    ),
    path(
        '<int:conf_pk>/api/compose/form_parts/',
        views.get_compose_form_components,
        name='api-get-compose-form-components',
    ),
    path('help/compose/', views.help_compose, name='help-compose'),

    #########################################################################
    path('<int:conf_pk>/api/mailing_lists/', api.list_mailing_lists, name='list-mailing-lists'),
    path('<int:conf_pk>/api/mailing_lists/<str:name>/', api.mailing_list_details, name='mailing-list-details'),
    path('<int:conf_pk>/api/users/', api.list_users, name='list-users'),
    path('<int:conf_pk>/api/preview/user/', api.render_user_message_preview, name='render-preview-user'),
    # path('<int:conf_pk>/api/users/search/', api.search_users, name='search-users'),
]
