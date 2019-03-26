from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from users.models import generate_avatar
from .forms import PersonalForm, ProfessionalForm

User = get_user_model()

@login_required
def personal(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = PersonalForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()

            if not profile.avatar:
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
            request.user.has_finished_registration = True
            request.user.save()
            return redirect('user-details', pk=request.user.pk)
    else:
        form = ProfessionalForm(instance=profile)
    return render(request, 'registration/professional.html', {
        'form': form
    })
