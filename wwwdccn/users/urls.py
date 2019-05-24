from django.urls import path

from . import views


app_name = 'users'

urlpatterns = [
    path('search/', views.search_users, name='search'),
    path('profile/overview/', views.profile_overview, name='profile-overview'),
    path('profile/account/', views.profile_account, name='profile-account'),
    path('profile/personal/', views.profile_personal, name='profile-personal'),
    path('profile/professional/', views.profile_professional,
         name='profile-professional'),
    path('profile/reviewer/', views.profile_reviewer, name='profile-reviewer'),
    path('email/update/', views.update_email, name='update-email'),
    path('subscriptions/update/', views.update_subscriptions,
         name='update-subscriptions'),
    path('password/update/', views.update_password, name='update-password'),
    path('avatar/update/', views.update_avatar, name='update-avatar'),
    path('avatar/delete/', views.delete_avatar, name='delete-avatar'),
    path('delete/', views.delete_account, name='delete'),
]