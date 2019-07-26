from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from review.forms import EditReviewForm
from review.models import Review


def validate_reviewer_access(user, review):
    if user != review.reviewer.user:
        raise Http404


@login_required
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


@login_required
@require_POST
def decline_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    validate_reviewer_access(request.user, review)
    paper_pk = review.paper.pk

    # Send email to chairs:
    context = {
        'user': request.user,
        'review': review,
        'protocol': settings.SITE_PROTOCOL,
        'domain': settings.SITE_DOMAIN,
    }
    text = render_to_string('review/email/review_declined_by_user.txt', context)
    conference = review.reviewer.conference
    send_mail(
        f"[DCCN2019] Refuse to review submission #{review.paper.pk}",
        message=text,
        recipient_list=[chair.email for chair in conference.chairs.all()],
        from_email=settings.DEFAULT_FROM_EMAIL,
        fail_silently=False,
    )

    # Delete the review:
    review.delete()
    messages.warning(request, f'You refused to review paper #{paper_pk}')
    return redirect('user_site:reviews')
