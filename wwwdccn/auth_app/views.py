from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.generic import FormView
from django.core.mail import send_mail, EmailMultiAlternatives

from .forms import SignUpForm

User = get_user_model()


class SignUpView(FormView):
    template_name = 'auth_app/signup.html'
    form_class = SignUpForm

    def form_valid(self, form):
        user = form.save()
        user.is_active = True
        user.save()
        login(self.request, user)

        context = {
            'email': user.email,
            'protocol': 'https' if self.request.is_secure() else "http",
            'domain': self.request.get_host(),
        }
        html = render_to_string('auth_app/email/welcome.html', context)
        text = render_to_string('auth_app/email/welcome.txt', context)
        send_mail(
            'Welcome to DCCN Conference Registration System!',
            message=text,
            html_message=html,
            recipient_list=[user.email],
            from_email=settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
        )
        return redirect('register')


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'auth_app/password_reset_done.html'
