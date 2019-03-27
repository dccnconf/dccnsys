from django.urls import path

from .views import profile, submissions


urlpatterns = [
    path('', submissions.user_details, name='submissions'),

    path('profile/overview/', profile.overview_page, name='profile-overview'),
    path('profile/account/', profile.account_page, name='profile-account'),
    path('profile/personal/', profile.personal_settings, name='profile-personal'),
    path('profile/professional/', profile.professional_settings, name='profile-professional'),
    path('profile/reviewer/', profile.reviewer_settings, name='profile-reviewer'),
    path('profile/update/email/', profile.update_email, name='profile-update-email'),
    path('profile/update/subscriptions/', profile.update_subscriptions, name='profile-update-subscriptions'),
    path('profile/update/password/', profile.update_password, name='profile-update-password'),
    path('profile/update/avatar/', profile.update_avatar, name='profile-update-avatar'),
    path('profile/delete/', profile.delete_account, name='profile-delete'),
    path('profile/delete/avatar/', profile.delete_avatar, name='profile-delete-avatar'),
]
