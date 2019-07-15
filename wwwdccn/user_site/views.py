from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from review.models import Review
from submissions.models import Submission


@login_required
def submissions(request):
    return render(request, 'user_site/submissions.html', {
        'submissions': Submission.objects.filter(authors__user=request.user),
    })


@login_required
def reviews(request):
    return render(request, 'user_site/reviews.html', {
        'reviews': Review.objects.filter(reviewer__user=request.user),
    })
