from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, \
    PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView, \
    PasswordResetDoneView

from .views import SignUpView

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),

    path('login/', LoginView.as_view(
        redirect_authenticated_user=True,
        template_name='auth_app/login.html',
    ), name='login'),

    path('logout/', LogoutView.as_view(), name='logout'),

    path('password_reset/', PasswordResetView.as_view(
        template_name='auth_app/password_reset.html',
        email_template_name='auto_app/email/password_reset.txt',
        html_email_template_name='auth_app/email/password_reset.html',
        subject_template_name='auth_app/email/password_reset_subject.txt'
    ), name='password_reset'),

    path(
        'password_reset/done/',
        PasswordResetDoneView.as_view(
            template_name='auth_app/password_reset_done.html',
        ),
        name='password_reset_done'),

    path(
        'password_reset/<str:uidb64>/<str:token>/',
        PasswordResetConfirmView.as_view(
            template_name='auth_app/password_reset_confirm.html',
        ),
        name='password_reset_confirm'),

    path(
        'password_reset/complete/',
        PasswordResetCompleteView.as_view(
            template_name='auth_app/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
