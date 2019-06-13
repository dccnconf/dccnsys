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
def submissions_list(request, pk, page=1):
    conference = get_object_or_404(Conference, pk=pk)
    form = FilterSubmissionsForm(request.GET, instance=conference)
    submissions = list(conference.submission_set.all())

    if form.is_valid():
        term = form.cleaned_data['term']
        types = [int(t) for t in form.cleaned_data['types']]
        topics = [int(topic) for topic in form.cleaned_data['topics']]
        status = form.cleaned_data['status']
        countries = form.cleaned_data['countries']
        affiliations = form.cleaned_data['affiliations']

        if term:
            words = term.lower().split()
            submissions = [
                sub for sub in submissions
                if all(word in sub.title.lower() or
                       any(word in a.user.profile.get_full_name().lower()
                           for a in sub.authors.all()) or
                       any(word in a.user.profile.get_full_name_rus().lower()
                           for a in sub.authors.all())
                       for word in words)
            ]

        if topics:
            submissions = [
                sub for sub in submissions
                if any(topic in [t.pk for t in sub.topics.all()]
                       for topic in topics)
            ]

        if types:
            submissions = [sub for sub in submissions
                           if sub.stype and sub.stype.pk in types]

        if status:
            submissions = [sub for sub in submissions if sub.status in status]

        if countries:
            submissions = [
                sub for sub in submissions
                if any(author.user.profile.country.code in countries
                       for author in sub.authors.all())
            ]

        if affiliations:
            submissions = [
                sub for sub in submissions
                if any(author.user.profile.affiliation in affiliations
                       for author in sub.authors.all())
            ]

    num_items = len(submissions)
    num_pages = int(math.ceil(len(submissions) / ITEMS_PER_PAGE))
    start_index = (page-1) * ITEMS_PER_PAGE
    end_index = min(page * ITEMS_PER_PAGE, num_items)
    submissions = submissions[start_index: end_index]

    return render(request, 'chair/submissions_list.html', context={
        'conference': conference,
        'submissions': submissions,
        'filter_form': form,
        'num_pages': num_pages,
        'num_items': num_items,
        'page': page,
        'next_page': page + 1,
        'prev_page': page - 1,
        'first_index': start_index + 1,
        'last_index': end_index,
        'is_first_page': start_index == 0,
        'is_last_page': end_index == num_items,
    })


@chair_required
@require_GET
def users_list(request, pk, page=1):
    conference = get_object_or_404(Conference, pk=pk)
    users = User.objects.all()
    form = FilterUsersForm(request.GET, instance=conference)

    if form.is_valid():
        term = form.cleaned_data['term']
        attending = form.cleaned_data['attending']
        countries = form.cleaned_data['countries']
        affiliations = form.cleaned_data['affiliations']

        if term:
            words = term.lower().split()
            users = [
                user for user in users
                if all(any(word in string for string in [
                    user.profile.get_full_name().lower(),
                    user.profile.get_full_name_rus().lower(),
                    user.profile.affiliation.lower(),
                    user.profile.get_country_display().lower()
                    ]) for word in words)
            ]

        if attending:
            users = [
                user for user in users
                if any(author.submission.conference == conference
                       for author in user.authorship.all())
            ]

        if countries:
            users = [
                user for user in users if user.profile.country.code in countries
            ]

        if affiliations:
            users = [
                user for user in users
                if user.profile.affiliation in affiliations
            ]

    num_items = len(users)
    num_pages = int(math.ceil(len(users) / ITEMS_PER_PAGE))
    start_index = (page-1) * ITEMS_PER_PAGE
    end_index = min(page * ITEMS_PER_PAGE, num_items)
    users = users[start_index: end_index]

    return render(request, 'chair/users_list.html', context={
        'conference': conference,
        'users': users,
        'filter_form': form,
        'num_pages': num_pages,
        'num_items': num_items,
        'page': page,
        'next_page': page + 1,
        'prev_page': page - 1,
        'first_index': start_index + 1,
        'last_index': end_index,
        'is_first_page': start_index == 0,
        'is_last_page': end_index == num_items,
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
