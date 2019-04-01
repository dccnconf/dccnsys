from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from submissions.models import Submission


@login_required
def user_details(request):
    return render(request, 'user_site/submissions.html', {
        'submissions': Submission.objects.filter(authors__user=request.user)
    })
