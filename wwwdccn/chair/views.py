import math

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from chair.forms import FilterSubmissionsForm, FilterUsersForm
from conferences.decorators import chair_required
from conferences.models import Conference


ITEMS_PER_PAGE = 10


User = get_user_model()


@chair_required
@require_GET
def dashboard(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return render(request, 'chair/dashboard.html', context={
        'conference': conference,
    })


@chair_required
@require_GET
def submissions_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    form = FilterSubmissionsForm(request.GET, instance=conference)
    submissions = list(conference.submission_set.all())

    if form.is_valid():
        submissions = form.apply(submissions)

    return render(request, 'chair/submissions_list.html', context={
        'conference': conference,
        'submissions': submissions,
        'filter_form': form,
    })


@chair_required
@require_GET
def users_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    users = User.objects.all()
    form = FilterUsersForm(request.GET, instance=conference)

    if form.is_valid():
        users = form.apply(users)

    return render(request, 'chair/users_list.html', context={
        'conference': conference,
        'users': users,
        'filter_form': form,
    })


@chair_required
@require_GET
def user_details(request, pk, user_pk):
    conference = get_object_or_404(Conference, pk=pk)
    user = get_object_or_404(User, pk=user_pk)
    return render(request, 'chair/user_details.html', context={
        'conference': conference,
        'member': user,
    })
