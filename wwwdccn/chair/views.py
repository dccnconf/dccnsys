from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from chair.forms import FilterSubmissionsForm
from conferences.decorators import chair_required
from conferences.models import Conference


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
            submissions = [sub for sub in submissions if sub.stype.pk in types]

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
    return render(request, 'chair/users_list.html', context={
        'conference': conference,
        'users': users,
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
