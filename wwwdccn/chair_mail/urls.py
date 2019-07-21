from django.urls import path

from . import views


app_name = 'chair_mail'

urlpatterns = [
    path('<int:conf_pk>/overview/', views.overview, name='overview'),
    path('<int:conf_pk>/template/', views.message_template, name='message-template'),
    path('<int:conf_pk>/template/create/', views.create_template, name='create-template'),

    path('<int:conf_pk>/template/send_test_message/', views.send_template_test_message, name='send-template-test-message'),
]
