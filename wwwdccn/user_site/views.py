from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from review.models import Review
from submissions.models import Submission


@login_required
def submissions_list(request):
    return render(request, 'user_site/submissions.html', {
        'submissions': Submission.objects.filter(authors__user=request.user),
    })


@login_required
def reviews_list(request):
    submissions = Submission.objects.filter(authors__user=request.user)
    return render(request, 'user_site/reviews.html', {
        'numSubmissions': len(submissions),
        'reviews': Review.objects.filter(reviewer__user=request.user),
    })
