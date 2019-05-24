import base64

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from users.forms import PersonalForm, ProfessionalForm, UpdateEmailForm, \
    SubscriptionsForm, DeleteUserForm, DeleteAvatarForm
from users.models import change_avatar


User = get_user_model()


@login_required
@require_GET
def profile_overview(request):
    return render(request, 'users/profile_overview.html')


@login_required
@require_POST
def update_avatar(request):
    profile = request.user.profile
    # Received base64 string starts with 'data:image/jpeg;base64,........'
    # We need to use 'jpeg' as an extension and everything after base64,
    # as the image itself:
    fmt, imgstr = request.POST['avatar'].split(';base64')
    ext = fmt.split('/')[-1]
    if ext == 'svg+xml':
        ext = 'svg'
    img = ContentFile(base64.b64decode(imgstr), name=f'{profile.pk}.{ext}')
    change_avatar(request.user.profile, img)
    return redirect('users:profile-account')


@login_required
@require_POST
def delete_avatar(request):
    form = DeleteAvatarForm(request.POST, instance=request.user.profile)
    form.save()
    return redirect('users:profile-overview')


@login_required
@require_GET
def profile_account(request):
    notifications_form = SubscriptionsForm(instance=request.user.subscriptions)
    delete_user_form = DeleteUserForm(user=request.user)
    return render(request, 'users/profile_account.html', {
        'notifications_form': notifications_form,
        'delete_user_form': delete_user_form,
    })


@login_required
@require_POST
def update_email(request):
    form = UpdateEmailForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, _('Email was updated'))
    else:
        messages.error(request, _('Failed to update email'))
    return redirect('users:profile-account')


@login_required
@require_POST
def update_password(request):
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, _('Password was updated'))
    else:
        messages.error(request, _('Failed to update password'))
    return redirect('users:profile-account')


@login_required
@require_POST
def update_subscriptions(request):
    form = SubscriptionsForm(request.POST, instance=request.user.subscriptions)
    if form.is_valid():
        form.save()
        messages.success(request, _('Notifications settings updated'))
    else:
        messages.error(request, _('Failed to update notifications settings'))
    return redirect('users:profile-account')


@login_required
@require_POST
def delete_account(request):
    form = DeleteUserForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        return redirect('home')

    messages.error(request, _('Failed to delete account'))
    return redirect('users:profile-account')


@login_required
def profile_personal(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = PersonalForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Personal settings were updated'))
            return redirect('users:profile-personal')
    else:
        form = PersonalForm(instance=profile)
    return render(request, 'users/profile_personal.html', {
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
            return redirect('users:profile-professional')
    else:
        form = ProfessionalForm(instance=profile)
    return render(request, 'users/profile_professional.html', {
        'form': form,
    })


@login_required
def profile_reviewer(request):
    return render(request, 'users/profile_reviewer.html')


#############################################################################
# AJAX
#############################################################################

@login_required
@require_GET
def search_users(request):
    # TODO: split query into words and match them all
    query = request.GET.get('q')
    users = User.objects.filter(
        Q(profile__first_name__icontains=query) |
        Q(profile__last_name__icontains=query) |
        Q(profile__first_name_rus__icontains=query) |
        Q(profile__last_name_rus__icontains=query)
    )
    data = {'users': [{
        'id': user.id,
        'first_name': user.profile.first_name,
        'last_name': user.profile.last_name,
        'first_name_rus': user.profile.first_name_rus,
        'middle_name_rus': user.profile.middle_name_rus,
        'last_name_rus': user.profile.last_name_rus,
        'affiliation': user.profile.affiliation,
        'avatar': user.profile.avatar.url if user.profile.avatar else '',
    } for user in users]}
    return JsonResponse(data)
