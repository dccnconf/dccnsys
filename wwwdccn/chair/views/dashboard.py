from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from chair.utility import validate_chair_access
from conferences.models import Conference
from submissions.models import Submission
from users.models import User


@require_GET
def overview(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    submission_types = tuple({
        'length': st.submissions.count(),
        'name': st.name.capitalize(),
    } for st in conference.submissiontype_set.all())

    num_submissions = Submission.objects.filter(stype__isnull=False).count()

    num_authors = User.objects.filter(
        authorship__submission__conference__pk=conf_pk
    ).count()

    return render(request, 'chair/dashboard/dashboard.html', context={
        'conference': conference,
        'num_submissions': num_submissions,
        'num_authors': num_authors,
    })
