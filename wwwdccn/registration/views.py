from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from users.models import generate_avatar
from users.forms import PersonalForm, ProfessionalForm, SubscriptionsForm

User = get_user_model()


@login_required
def personal(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = PersonalForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.avatar = generate_avatar(profile)
            profile.save()
            return redirect('register-professional')
    else:
        form = PersonalForm(instance=profile)
    return render(request, 'registration/personal.html', {
        'form': form
    })

@login_required
def professional(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfessionalForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('register-subscriptions')
    else:
        form = ProfessionalForm(instance=profile)
    return render(request, 'registration/professional.html', {
        'form': form
    })


@login_required
def subscriptions(request):
    subscriptions = request.user.subscriptions
    if request.method == 'POST':
        form = SubscriptionsForm(request.POST, instance=subscriptions)
        if form.is_valid():
            form.save()
            request.user.has_finished_registration = True
            request.user.save()
            return redirect('home')
    else:
        form = SubscriptionsForm(instance=subscriptions)
    return render(request, 'registration/subscriptions.html', {
        'form': form
    })
