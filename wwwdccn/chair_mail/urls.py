from django.urls import path

from . import views


app_name = 'chair_mail'

urlpatterns = [
    path('<int:conf_pk>/overview/', views.overview, name='overview'),
    path('<int:conf_pk>/html_template/', views.html_template, name='html_template'),
    path('<int:conf_pk>/plain_template/', views.plain_template, name='plain_template'),
]
