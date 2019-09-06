import csv
import functools
from datetime import datetime

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import ugettext_lazy as _

from chair.forms import FilterSubmissionsForm, \
    ChairUploadReviewManuscriptForm, AssignReviewerForm
from chair.utility import validate_chair_access, build_paged_view_context
from conferences.decorators import chair_required
from conferences.models import Conference
from review.forms import UpdateVolumeForm
from review.models import Review, ReviewStats, Decision
from review.utilities import count_required_reviews, qualify_score, \
    UNKNOWN_QUALITY
from submissions.forms import SubmissionDetailsForm, AuthorCreateForm, \
    AuthorDeleteForm, AuthorsReorderForm, InviteAuthorForm
from submissions.models import Submission
from users.models import Profile


def submission_view(fn):
    @functools.wraps(fn)
    def wrapper(request, conf_pk, sub_pk, *args, **kwargs):
        conference = get_object_or_404(Conference, pk=conf_pk)
        submission = get_object_or_404(Submission, pk=sub_pk)
        validate_chair_access(request.user, conference)
        if submission.conference_id != conference.pk:
            raise Http404
        return fn(request, conference, submission, *args, **kwargs)
    return wrapper


@require_GET
def list_submissions(request, conf_pk, page=1):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    form = FilterSubmissionsForm(request.GET, instance=conference)
    submissions = conference.submission_set.all()

    if form.is_valid():
        submissions = form.apply(submissions)

    pks = [sub.pk for sub in submissions]

    context = build_paged_view_context(
        request, pks, page, 'chair:submissions-pages', {'conf_pk': conf_pk}
    )
    context.update({
        'conference': conference,
        'filter_form': form,
    })
    return render(request, 'chair/submissions/submissions_list.html',
                  context=context)


@require_GET
@submission_view
def feed_item(request, conference, submission):
    if submission.status == Submission.SUBMITTED:
        return render(request, 'chair/submissions/feed/card_submitted.html', {
            'conf_pk': conference.pk,
            'submission': submission,
        })

    elif submission.status == Submission.UNDER_REVIEW:
        stats, _ = ReviewStats.objects.get_or_create(conference=conference)

        # Fill reviews data - a list of scores with data, and warnings:
        reviews_data = []
        num_incomplete, num_missing = 0, 0
        for review in submission.reviews.all():
            score = review.average_score()
            quality = qualify_score(score, stats=stats)
            reviews_data.append({
                'quality': quality,
                'score': f'{score:.1f}' if score > 0 else '?',
            })
            if score == 0:
                num_incomplete += 1
        num_required = count_required_reviews(submission)
        if num_required > len(reviews_data):
            num_missing = num_required - len(reviews_data)
            for _ in range(num_required - len(reviews_data)):
                reviews_data.append({'quality': UNKNOWN_QUALITY, 'score': '-'})

        warnings = []
        if num_incomplete > 0:
            warnings.append(f'{num_incomplete} reviews are not finished')
        if num_missing > 0:
            warnings.append(f'{num_missing} reviews are not assigned')

        return render(request, 'chair/reviews/_submission_feed_item.html', {
            'submission': submission,
            'conf_pk': conference.pk,
            'decision_data': _get_decision_form_data(submission),
            'reviews_data': reviews_data,
            'warnings': warnings,
        })

    elif submission.status == Submission.ACCEPTED:
        return render(request, 'chair/submissions/feed/card_accepted.html', {
            'conf_pk': conference.pk,
            'submission': submission,
            'decision': submission.review_decision.first(),
            'form_data': _get_volume_form_data(submission),
        })

    elif submission.status == Submission.REJECTED:
        return render(request, 'chair/submissions/feed/card_rejected.html', {
            'conf_pk': conference.pk,
            'submission': submission,
        })


@require_POST
def volume_control_panel(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.get(pk=sub_pk)
    decision = submission.review_decision.first()
    form = UpdateVolumeForm(request.POST, instance=decision)
    if request.method == 'POST' and form.is_valid():
        form.save()
    return render(request, 'chair/accepted_papers/_feed_item.html', {
        'conf_pk': conference.pk,
        'submission': submission,
        'decision': submission.review_decision.first(),
        'form_data': _get_volume_form_data(submission),
    })


@require_POST
def commit_volume(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.get(pk=sub_pk)
    decision = submission.review_decision.first()
    decision.commit()
    return render(request, 'chair/accepted_papers/_feed_item.html', {
        'conf_pk': conference.pk,
        'submission': submission,
        'decision': submission.review_decision.first(),
        'form_data': _get_volume_form_data(submission),
    })


def _get_volume_form_data(submission):
    decision = submission.review_decision.first()
    proc_type = decision.proc_type
    volume = decision.volume if decision else None
    default_option = [('', 'Not selected')]

    data_volume = {
        'hidden': False,
        'value': '', 'display': default_option[0][-1],
        'options': default_option + [
            (vol.pk, vol.name) for vol in proc_type.volumes.all()],

    }
    if volume:
        data_volume.update({'value': volume.pk, 'display': volume.name})
    return {
        'volume': data_volume,
        'committed': decision.committed if decision else True
    }


def _get_decision_form_data(submission):
    decision = submission.review_decision.first()
    proc_type = decision.proc_type if decision else None
    volume = decision.volume if decision else None
    default_option = [('', 'Not selected')]

    # 1) Filling data_decision value and display:
    data_decision = {'hidden': False, 'options': Decision.DECISION_CHOICES}
    decision_value = Decision.UNDEFINED if not decision else decision.decision
    data_decision['value'] = decision_value
    data_decision['display'] = [
        opt[1] for opt in Decision.DECISION_CHOICES if opt[0] == decision_value
    ][0]

    # 2) Fill proceedings type if possible:
    stype = submission.stype
    data_proc_type = {
        'hidden': decision_value != Decision.ACCEPT,
        'value': '', 'display': default_option[0][-1],
    }
    if not data_proc_type['hidden']:
        data_proc_type['options'] = default_option + [
            (pt.pk, pt.name) for pt in stype.possible_proceedings.all()]
        if proc_type:
            data_proc_type.update({
                'value': proc_type.pk, 'display': proc_type.name
            })

    # 3) Fill volumes if possible:
    data_volume = {
        'hidden': data_proc_type['value'] == '',
        'value': '', 'display': default_option[0][-1],
    }
    if not data_volume['hidden']:
        data_volume['options'] = default_option + [
            (vol.pk, vol.name) for vol in proc_type.volumes.all()]
        if volume:
            data_volume.update({'value': volume.pk, 'display': volume.name})

    # 4) Collect everything and output:
    return {
        'decision': data_decision,
        'proc_type': data_proc_type,
        'volume': data_volume,
        'committed': decision.committed if decision else True
    }


@require_GET
@submission_view
def overview(request, conference, submission):
    # If the request is AJAX, then we render only the overview as for
    # modal dialog:
    if request.is_ajax():
        return render(request,
                      'chair/components/submission_overview_modal.html',
                      context={'submission': submission})

    # Otherwise, render separate chair view page:
    status = submission.status
    warnings = submission.warnings()
    # has_review_manuscript = not (not submission.review_manuscript)
    actions = {
        'review': (status == Submission.SUBMITTED and not warnings),
        'revoke_review': status == Submission.UNDER_REVIEW,
    }
    return render(request, 'chair/submissions/submission_overview.html', context={
        'conference': conference,
        'submission': submission,
        'warnings': warnings,
        'actions': actions,
        'active_tab': 'overview',
    })


@submission_view
def metadata(request, conference, submission):
    if request.method == 'POST':
        form = SubmissionDetailsForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(request, f'Submission #{submission.pk} updated')
    else:
        form = SubmissionDetailsForm(instance=submission)
    return render(request, 'chair/submissions/submission_metadata.html', context={
        'submission': submission,
        'conference': conference,
        'form': form,
        'active_tab': 'metadata',
    })


@require_GET
@submission_view
def authors(request, conference, submission):
    return render(request, 'chair/submissions/submission_authors.html', context={
        'conference': conference,
        'submission': submission,
        'active_tab': 'authors',
    })


@require_POST
@submission_view
def create_author(request, conference, submission):
    form = AuthorCreateForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect(
        'chair:submission-authors', conf_pk=conference.pk, sub_pk=submission.pk
    )


@require_POST
@submission_view
def delete_author(request, conference, submission):
    form = AuthorDeleteForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect(
        'chair:submission-authors', conf_pk=conference.pk, sub_pk=submission.pk
    )


@require_POST
@submission_view
def reorder_authors(request, conference, submission):
    form = AuthorsReorderForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect(
        'chair:submission-authors', conf_pk=conference.pk, sub_pk=submission.pk
    )


@submission_view
def invite_author(request, conference, submission):
    form = InviteAuthorForm(request.POST)
    if form.is_valid():
        form.save(request, submission)
        messages.success(request, _('Invitation sent'))
    else:
        messages.warning(request, _('Error sending invitation'))
    return redirect(
        'chair:submission-authors', conf_pk=conference.pk, sub_pk=submission.pk
    )


@submission_view
def review_manuscript(request, conference, submission):
    if request.method == 'POST':
        form = ChairUploadReviewManuscriptForm(
            request.POST,
            request.FILES,
            instance=submission
        )

        # We save current file (if any) for two reasons:
        # 1) if this file is not empty and user uploaded a new file, we
        #    are going to delete this old file (in case of valid form);
        #    and
        # 2) it is going to be assigned instead of TemporaryUploadedFile
        #    object in case of form validation error.
        old_file = (submission.review_manuscript.file
                    if submission.review_manuscript else None)
        if form.is_valid():
            # If the form is valid and user provided a new file, we
            # delete original file first. Otherwise Django will add a
            # random suffix which will break our storage strategy.
            if old_file and request.FILES:
                submission.review_manuscript.storage.delete(
                    old_file.name
                )
            form.save()
            messages.success(request, _('Manuscript updated'))
            return redirect(
                'chair:submission-review-manuscript',
                conf_pk=conference.pk, sub_pk=submission.pk
            )
        else:
            # If the form is invalid (e.g. title is not provided),
            # but the user tried to upload a file, a new
            # TemporaryUploadedFile object will be created and,
            # which is more important, it will be assigned to
            # `note.document` field. We want to avoid this to make sure
            # that until the form is completely valid previous file
            # is not re-written. To do it we assign the `old_file`
            # value to both cleaned_data and note.document:
            form.cleaned_data['review_manuscript'] = old_file
            submission.review_manuscript.document = old_file
            messages.warning(request, _('Error uploading manuscript'))
    else:
        form = ChairUploadReviewManuscriptForm(instance=submission)

    return render(
        request,
        'chair/submissions/submission_review_manuscript.html',
        context={
            'submission': submission,
            'conference': conference,
            'form': form,
            'active_tab': 'review-manuscript',
        }
    )


@submission_view
def delete_review_manuscript(request, conference, submission):
    file_name = submission.get_review_manuscript_name()
    if submission.review_manuscript:
        submission.review_manuscript.delete()
        messages.info(request, f'Manuscript {file_name} was deleted')
    return redirect(
        'chair:submission-review-manuscript',
        conf_pk=conference.pk, sub_pk=submission.pk
    )


@require_POST
@submission_view
def start_review(request, conference, submission):
    if submission.status in [Submission.SUBMITTED, Submission.ACCEPTED,
                             Submission.REJECTED]:
        submission.status = Submission.UNDER_REVIEW
        submission.save()
        decision = submission.review_decision.first()
        if decision:
            decision.committed = False
            decision.save()
    return redirect(request.GET.get('next', ''))


# noinspection PyUnusedLocal
@require_POST
@submission_view
def revoke_review(request, conference, submission):
    if submission.status == Submission.UNDER_REVIEW:
        submission.status = Submission.SUBMITTED
        submission.save()
    return redirect(request.GET.get('next', ''))


@require_GET
@submission_view
def reviews(request, conference, submission):
    return render(request, 'chair/submissions/submission_reviews.html', context={
        'submission': submission,
        'conference': conference,
        'assign_reviewer_form': AssignReviewerForm(submission=submission),
    })


@submission_view
def emails(request, conference, submission):
    return render(request, 'chair/submissions/submission_emails.html', context={
        'submission': submission,
        'conference': conference,
        'msg_list': submission.group_emails.all().order_by('-sent_at'),
    })


@require_POST
@submission_view
def assign_reviewer(request, conference, submission):
    form = AssignReviewerForm(request.POST, submission=submission)
    if form.is_valid():
        form.save()
    return redirect(
        'chair:submission-reviewers',
        conf_pk=conference.pk, sub_pk=submission.pk
    )


# noinspection PyUnusedLocal
@require_POST
@submission_view
def delete_review(request, conference, submission, rev_pk):
    review = get_object_or_404(Review, pk=rev_pk)
    if review.paper != submission:
        raise Http404
    review.delete()
    return redirect(
        'chair:submission-reviewers',
        conf_pk=conference.pk, sub_pk=submission.pk)


@require_POST
def create_submission(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.create(conference=conference)
    return redirect('chair:submission-metadata', conf_pk=conf_pk,
                    sub_pk=submission.pk)


@require_POST
def delete_submission(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)
    submission.delete()
    messages.warning(request, f'Submission #{sub_pk} deleted')
    return redirect('chair:submissions', conf_pk=conf_pk)
