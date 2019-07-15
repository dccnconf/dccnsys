from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from review.forms import EditReviewForm
from review.models import Review


def validate_reviewer_access(user, review):
    if user != review.reviewer.user:
        raise Http404


def review_details(request, pk):
    review = get_object_or_404(Review, pk=pk)
    validate_reviewer_access(request.user, review)
    if request.method == 'POST':
        edit_form = EditReviewForm(request.POST, instance=review)
        if edit_form.is_valid():
            edit_form.save()
            return redirect('review:review-details', pk=pk)
    else:
        edit_form = EditReviewForm(instance=review)
    return render(request, 'review/review_details.html', context={
        'review': review,
        'edit_form': edit_form,
    })
