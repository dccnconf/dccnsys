from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from conferences.utilities import validate_chair_access
from review.forms import EditReviewForm, UpdateDecisionForm
from review.models import Review, Decision
from submissions.models import Submission


def validate_reviewer_access(user, review):
    if user != review.reviewer.user:
        raise Http404


@login_required
def review_details(request, pk):
    review = get_object_or_404(Review, pk=pk)
    validate_reviewer_access(request.user, review)
    if request.method == 'POST':
        if review.paper.status == Submission.UNDER_REVIEW:
            edit_form = EditReviewForm(request.POST, instance=review)
            if edit_form.is_valid():
                edit_form.save()
                return redirect('review:review-details', pk=pk)
        else:
            return HttpResponseForbidden()
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
    if review.paper.status != Submission.UNDER_REVIEW:
        return HttpResponseForbidden()

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


#
# API
#
@require_POST
def update_decision(request, sub_pk):
    """Update the first `ReviewDecision` object associated with a given
    submission. If it doesn't exist, create one.

    This view is called only in AJAX and returns a `JsonResponse` with either
    `200 OK`, or `500` with serialized form errors.
    """
    submission = get_object_or_404(Submission, pk=sub_pk)
    validate_chair_access(request.user, submission.conference)
    decision = submission.review_decision.first()
    if not decision:
        decision = Decision.objects.create(submission=submission)
    form = UpdateDecisionForm(request.POST, instance=decision)
    print(form)
    if form.is_valid():
        form.save()
        return JsonResponse(status=200, data={})
    return JsonResponse(status=500, data={'errors': form.errors})


# noinspection PyUnusedLocal
@require_POST
def commit_decision(request, sub_pk):
    """Call `ReviewDecision.commit()` method.

    This action may cause submission status change, emails sending, etc.
    See `Decision` and `Submission` models code for more information.
    """
    submission = get_object_or_404(Submission, pk=sub_pk)
    validate_chair_access(request.user, submission.conference)
    decision = submission.review_decision.first()
    if not decision:
        raise JsonResponse(status=404, data={'error': 'no decision exists'})
    decision.commit()
    return JsonResponse(status=200, data={})
