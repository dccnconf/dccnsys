import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.core.mail import send_mail

from .forms import SignUpForm

User = get_user_model()


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Check recaptcha. This code taken from
            #  https://medium.com/valus/invisible-recaptcha-django-ed06201161d5
            recaptcha_response = request.POST.get('g-recaptcha-response')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            data = urlencode(values).encode()
            req = Request(url, data=data)

            response = urlopen(req)
            result = json.loads(response.read().decode())
            if result['success']:
                user = form.save()
                user.is_active = True
                user.save()
                login(request, user)

                context = {
                    'email': user.email,
                    'protocol': 'https' if request.is_secure() else "http",
                    'domain': request.get_host(),
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
    else:
        form = SignUpForm()
    return render(request, 'auth_app/signup.html', {
        'site_key': settings.RECAPTCHA_SITE_KEY,
        'form': form,
    })


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'auth_app/password_reset_done.html'
