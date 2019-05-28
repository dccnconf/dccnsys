from django.shortcuts import get_object_or_404, render

from conferences.decorators import chair_required
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
    })
