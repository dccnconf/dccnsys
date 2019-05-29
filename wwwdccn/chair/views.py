from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from chair.forms import FilterSubmissionsForm
from conferences.decorators import chair_required
from conferences.helpers import get_authors_of
from conferences.models import Conference


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
        topics = [int(topic) for topic in form.cleaned_data['topics']]
        status = form.cleaned_data['status']
        countries = [int(cnt) for cnt in form.cleaned_data['countries']]
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

        print(f'Topics: {topics}')
        print(f'Status: {status}')
        print(f'Countries: {countries}')
        print(f'Affiliations: {affiliations}')

    return render(request, 'chair/submissions.html', context={
        'conference': conference,
        'submissions': submissions,
        'filter_form': form,
    })


@chair_required
def authors_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    authors = get_authors_of(conference.submission_set.all())
    return render(request, 'chair/authors.html', context={
        'conference': conference,
        'authors': authors,
    })
