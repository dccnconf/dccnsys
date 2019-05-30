from django.urls import path

from . import views


app_name = 'chair'

urlpatterns = [
    path('<int:pk>/', views.dashboard, name='home'),
    path('<int:pk>/submissions/', views.submissions_list, name='submissions'),
    path('<int:pk>/users/', views.users_list, name='users'),
    path('<int:pk>/users/<int:user_pk>', views.user_details, name='user'),
]
