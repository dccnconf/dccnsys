from django.urls import path

from . import views


app_name = 'chair'

urlpatterns = [
    path('/<int:pk>/', views.dashboard, name='home'),
    path('/<int:pk>/submissions/', views.submissions_list, name='submissions'),
    # path('users/', views.users_list, name='chair-users-list'),
]
