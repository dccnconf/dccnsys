from django.urls import path

from . import views


urlpatterns = [
    path('', views.user_details, name='user-details'),
    path('profile/overview/', views.profile_overview, name='profile-overview'),
    path('profile/account/', views.profile_account, name='profile-account'),
    path('profile/account/email/', views.user_update_email, name='user-email'),
    path('profile/account/notifications/', views.profile_update_notifications, name='profile-notifications'),
    path('profile/account/delete/', views.user_delete, name='user-delete'),
    path('profile/account/password/', views.user_update_password, name='user-password'),
    path('profile/account/avatar/', views.update_avatar, name='user-avatar'),
    path('profile/personal/', views.profile_personal, name='profile-personal'),
    path('profile/professional/', views.profile_professional, name='profile-professional'),
    path('profile/reviewer/', views.profile_reviewer, name='profile-reviewer'),
]
