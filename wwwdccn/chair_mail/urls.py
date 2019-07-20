from django.urls import path

from . import views


app_name = 'chair_mail'

urlpatterns = [
    path('<int:conf_pk>/overview/', views.overview, name='overview'),
    path('<int:conf_pk>/template/', views.message_template, name='message-template'),
    path('<int:conf_pk>/template/create/', views.create_template, name='create-template'),
]
