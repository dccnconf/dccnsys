import functools
import mimetypes

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import ugettext_lazy as _

from chair.forms import FilterSubmissionsForm, \
    ChairUploadReviewManuscriptForm, AssignReviewerForm
from conferences.utilities import validate_chair_access
from conferences.models import Conference
from review.models import Review, ReviewStats, Decision
from submissions.forms import SubmissionDetailsForm, AuthorCreateForm, \
    AuthorDeleteForm, AuthorsReorderForm, InviteAuthorForm
from submissions.models import Submission, Artifact


def submission_view(params='submission'):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(request, sub_pk, *args, **kwargs):
            submission = get_object_or_404(Submission, pk=sub_pk)
            conference = submission.conference
            validate_chair_access(request.user, conference)
            names = params.split(',')
            names.reverse()
            args = list(args)
            for name in names:
                if name == 'conference':
                    args = [conference] + args
                elif name == 'submission':
                    args = [submission] + args
                else:
                    raise ValueError(f'unsupported parameter name "{name}"')
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator


@require_GET
def list_submissions(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    form = FilterSubmissionsForm(request.GET, instance=conference)
    submissions = conference.submission_set.all()

    if form.is_valid():
        submissions = form.apply(submissions)

    pks = [sub.pk for sub in submissions]
    paginator = Paginator(pks, settings.ITEMS_PER_PAGE)
    page = paginator.page(request.GET.get('page', 1))

    context = {
        'conference': conference,
        'filter_form': form,
        'page': page,
    }
    return render(request, 'chair/submissions/list.html', context=context)


@require_POST
def create_submission(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.create(conference=conference)
    return redirect('chair:submission-metadata', sub_pk=submission.pk)


@require_POST
@submission_view('submission')
def delete_submission(request, submission):
    sub_pk, conf_pk = submission.pk, submission.conference_id
    submission.delete()
    messages.warning(request, f'Submission #{sub_pk} deleted')
    return redirect('chair:submissions', conf_pk=conf_pk)


#############################################################################
# SUBMISSIONS FEED
#############################################################################
@require_GET
@submission_view('submission,conference')
def feed_item(request, submission, conference):
    stats, _ = ReviewStats.objects.get_or_create(conference=conference)
    context = {
        'submission': submission,
        'review_stats': stats,
    }
    template_names = {
        Submission.SUBMITTED: 'chair/submissions/feed/card_submitted.html',
        Submission.UNDER_REVIEW: 'chair/submissions/feed/card_review.html',
        Submission.ACCEPTED: 'chair/submissions/feed/card_accepted.html',
        Submission.REJECTED: 'chair/submissions/feed/card_rejected.html',
    }
    if submission.status == Submission.UNDER_REVIEW:
        context['form_data'] = _build_decision_form_data(submission)
    elif submission.status == Submission.ACCEPTED:
        context['decision'] = submission.review_decision.first()
        context['form_data'] = _build_decision_form_data(
            submission, hide_decision=True, hide_proc_type=True)
    return render(request, template_names[submission.status], context)


def _build_decision_form_data(submission, hide_decision=False,
                              hide_proc_type=False, hide_volume=False):
    decision = submission.review_decision.first()
    proc_type = decision.proc_type if decision else None
    volume = decision.volume if decision else None
    default_option = [('', 'Not selected')]

    # 1) Filling data_decision value and display:
    decision_value = Decision.UNDEFINED if not decision else decision.decision
    data_decision = {
        'hidden': hide_decision,
        'options': Decision.DECISION_CHOICES,
        'value': decision_value,
        'display': [opt[1] for opt in Decision.DECISION_CHOICES
                    if opt[0] == decision_value][0]
    }

    # 2) Fill proceedings type if needed and possible:
    data_proc_type = {
        'hidden': hide_proc_type or decision_value != Decision.ACCEPT,
        'value': proc_type.pk if proc_type else '',
        'display': proc_type.name if proc_type else default_option[0][-1],
        'options': default_option + [
            (t.pk, t.name) for t in submission.stype.possible_proceedings.all()]
    }

    # 3) Fill volumes if possible:
    data_volume = {
        'hidden': hide_volume or not data_proc_type['value'],
        'value': volume.pk if volume else '',
        'display': volume.name if volume else default_option[0][-1],
        'options': default_option + [
            (vol.pk, vol.name) for vol in
            (proc_type.volumes.all() if proc_type else [])]
    }

    # 4) Collect everything and output:
    return {
        'decision': data_decision,
        'proc_type': data_proc_type,
        'volume': data_volume,
        'committed': decision.committed if decision else True
    }


#############################################################################
# TAB PAGES
#############################################################################
@require_GET
@submission_view('submission,conference')
def overview(request, submission, conference):
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
    return render(request, 'chair/submissions/submission_overview.html', {
        'submission': submission,
        'conference': conference,
        'warnings': warnings,
        'actions': actions,
        'active_tab': 'overview',
    })


@submission_view('submission,conference')
def metadata(request, submission, conference):
    if request.method == 'POST':
        form = SubmissionDetailsForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(request, f'Submission #{submission.pk} updated')
    else:
        form = SubmissionDetailsForm(instance=submission)
    return render(request, 'chair/submissions/submission_metadata.html', {
        'submission': submission,
        'conference': conference,
        'form': form,
        'active_tab': 'metadata',
    })


@require_GET
@submission_view('submission,conference')
def authors(request, submission, conference):
    return render(request, 'chair/submissions/submission_authors.html', {
        'submission': submission,
        'conference': conference,
        'active_tab': 'authors',
    })


@require_POST
@submission_view('submission')
def create_author(request, submission):
    form = AuthorCreateForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect('chair:submission-authors', sub_pk=submission.pk)


@require_POST
@submission_view('submission')
def delete_author(request, submission):
    form = AuthorDeleteForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect('chair:submission-authors', sub_pk=submission.pk)


@require_POST
@submission_view('submission')
def reorder_authors(request, submission):
    form = AuthorsReorderForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect('chair:submission-authors', sub_pk=submission.pk)


@submission_view('submission')
def invite_author(request, submission):
    form = InviteAuthorForm(request.POST)
    if form.is_valid():
        form.save(request, submission)
        messages.success(request, _('Invitation sent'))
    else:
        messages.warning(request, _('Error sending invitation'))
    return redirect('chair:submission-authors', sub_pk=submission.pk)


@submission_view('submission,conference')
def review_manuscript(request, submission, conference):
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
            return redirect('chair:submission-review-manuscript',
                            sub_pk=submission.pk)
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
        'chair/submissions/submission_review_manuscript.html', {
            'submission': submission, 'conference': conference, 'form': form,
            'active_tab': 'review-manuscript'}
    )


@submission_view('submission')
def delete_review_manuscript(request, submission):
    file_name = submission.get_review_manuscript_name()
    if submission.review_manuscript:
        submission.review_manuscript.delete()
        messages.info(request, f'Manuscript {file_name} was deleted')
    return redirect('chair:submission-review-manuscript', sub_pk=submission.pk)


@require_POST
@submission_view('submission')
def revoke_review(request, submission):
    if submission.status == Submission.UNDER_REVIEW:
        submission.status = Submission.SUBMITTED
        submission.save()
    return JsonResponse(data={})


@require_GET
@submission_view('submission,conference')
def reviews(request, submission, conference):
    return render(request, 'chair/submissions/submission_reviews.html', {
        'submission': submission,
        'conference': conference,
        'assign_reviewer_form': AssignReviewerForm(submission=submission),
    })


@submission_view('submission,conference')
def emails(request, submission, conference):
    return render(request, 'chair/submissions/submission_emails.html', context={
        'submission': submission,
        'conference': conference,
        'msg_list': submission.group_emails.all().order_by('-sent_at'),
        'active_tab': 'messages',
    })


@submission_view('submission,conference')
def camera_ready(request, submission, conference):
    return render(request, 'chair/submissions/tabs/camera_ready.html', context={
        'submission': submission,
        'conference': conference,
        'active_tab': 'camera-ready',
    })


@require_POST
@submission_view('submission')
def assign_reviewer(request, submission):
    form = AssignReviewerForm(request.POST, submission=submission)
    if form.is_valid():
        form.save()
    return redirect('chair:submission-reviewers', sub_pk=submission.pk)


# noinspection PyUnusedLocal
@require_POST
@submission_view('submission')
def delete_review(request, submission, rev_pk):
    review = get_object_or_404(Review, pk=rev_pk)
    if review.paper != submission:
        raise Http404
    review.delete()
    return redirect('chair:submission-reviewers', sub_pk=submission.pk)


#
# Overridden user methods:
#
@require_GET
def artifact_download(request, art_pk):
    artifact = get_object_or_404(Artifact, pk=art_pk)
    validate_chair_access(request.user, artifact.submission.conference)
    if artifact.file:
        filename = artifact.get_chair_download_name()
        mtype = mimetypes.guess_type(filename)[0]
        response = HttpResponse(artifact.file.file, content_type=mtype)
        response['Content-Disposition'] = f'filename={filename}'
        return response
    raise Http404


#
# API
#
# noinspection PyUnusedLocal
@require_POST
@submission_view('submission')
def start_review(request, submission):
    if submission.status in [Submission.SUBMITTED, Submission.ACCEPTED,
                             Submission.REJECTED]:
        submission.status = Submission.UNDER_REVIEW
        submission.save()
        decision = submission.review_decision.first()
        if decision:
            decision.committed = False
            decision.save()
    return JsonResponse(data={})
