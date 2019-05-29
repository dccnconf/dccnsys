from django.shortcuts import get_object_or_404, render

from conferences.decorators import chair_required
from conferences.helpers import get_authors_of
from conferences.models import Conference


@chair_required
def dashboard(request, pk):
    conference = get_object_or_404(Conference, pk=pk)

    return render(request, 'chair/dashboard.html', context={
        'conference': conference,
    })


@chair_required
def submissions_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return render(request, 'chair/submissions.html', context={
        'conference': conference,
        'submissions': conference.submission_set.all(),
    })


@chair_required
def authors_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    authors = get_authors_of(conference.submission_set.all())
    return render(request, 'chair/authors.html', context={
        'conference': conference,
        'authors': authors,
    })
