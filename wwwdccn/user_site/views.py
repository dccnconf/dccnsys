import base64

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import ugettext_lazy as _

from users.forms import PersonalForm, ProfessionalForm, UpdateEmailForm, \
    SubscriptionsForm, DeleteUserForm, DeleteAvatarForm
from users.models import update_avatar


User = get_user_model()


@login_required
def user_details(request):
    return render(request, 'user_site/submissions.html')


@login_required
def profile_overview(request):
    return render(request, 'user_site/profile_overview.html')


@login_required
@require_GET
def profile_account(request):
    notifications_form = SubscriptionsForm(instance=request.user.subscriptions)
    delete_user_form = DeleteUserForm(user=request.user)
    return render(request, 'user_site/profile_account.html', {
        'notifications_form': notifications_form,
        'delete_user_form': delete_user_form,
    })


@login_required
@require_POST
def user_update_email(request):
    form = UpdateEmailForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, _('Email was updated'))
    else:
        messages.error(request, _('Failed to update email'))
    return redirect('profile-account')


@login_required
@require_POST
def user_update_password(request):
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, _('Password was updated'))
    else:
        messages.error(request, _('Failed to update password'))
    return redirect('profile-account')


@login_required
@require_POST
def user_delete(request):
    form = DeleteUserForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        return redirect('home')

    messages.error(request, _('Failed to delete account'))
    return redirect('profile-account')


@login_required
@require_POST
def profile_update_notifications(request):
    form = SubscriptionsForm(request.POST, instance=request.user.subscriptions)
    if form.is_valid():
        form.save()
        messages.success(request, _('Notifications settings updated'))
    else:
        messages.error(request, _('Failed to update notifications settings'))
    return redirect('profile-account')


@login_required
@require_POST
def profile_update_avatar(request):
    profile = request.user.profile
    # Received base64 string starts with 'data:image/jpeg;base64,........'
    # We need to use 'jpeg' as an extension and everything after base64,
    # as the image itself:
    fmt, imgstr = request.POST['avatar'].split(';base64')
    ext = fmt.split('/')[-1]
    if ext == 'svg+xml':
        ext = 'svg'
    img = ContentFile(base64.b64decode(imgstr), name=f'{profile.pk}.{ext}')
    update_avatar(request.user.profile, img)
    return redirect('profile-account')


@login_required
@require_POST
def delete_avatar(request):
    form = DeleteAvatarForm(request.POST, instance=request.user.profile)
    form.save()
    return redirect('profile-overview')


@login_required
def profile_personal(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = PersonalForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Personal settings were updated'))
            return redirect('profile-personal')
    else:
        form = PersonalForm(instance=profile)
    return render(request, 'user_site/profile_personal.html', {
        'form': form,
    })


@login_required
def profile_professional(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfessionalForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Professional settings were updated'))
            return redirect('profile-professional')
    else:
        form = ProfessionalForm(instance=profile)
    return render(request, 'user_site/profile_professional.html', {
        'form': form,
    })


@login_required
def profile_reviewer(request):
    return render(request, 'user_site/profile_reviewer.html')
