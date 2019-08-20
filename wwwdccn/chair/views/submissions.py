import csv
import functools
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import ugettext_lazy as _

from chair.forms import FilterSubmissionsForm, \
    ChairUploadReviewManuscriptForm, AssignReviewerForm
from chair.utility import validate_chair_access, build_paged_view_context
from conferences.decorators import chair_required
from conferences.models import Conference
from review.models import Review
from submissions.forms import SubmissionDetailsForm, AuthorCreateForm, \
    AuthorDeleteForm, AuthorsReorderForm, InviteAuthorForm
from submissions.models import Submission, Author
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

    # auth_prs = {
    #     sub: Profile.objects.filter(user__authorship__submission=sub).values(
    #         'first_name', 'last_name', 'user__pk',
    #     )
    #     for sub in submissions
    # }
    # NOTE: may be slower than code above, but provides right ordering:

    # Collect possible actions:
    actions = {
        sub: {
            'review': sub.status == Submission.SUBMITTED and not sub.warnings(),
            'revoke_review': sub.status == Submission.UNDER_REVIEW,
            'assign_reviewers': sub.status == Submission.UNDER_REVIEW,
        }
        for sub in submissions
    }

    _reviews = {
        sub: sub.reviews.all() for sub in submissions
    }
    num_revs_incomplete = {
        sub: sub.reviews.filter(submitted=False).count() for sub in submissions
    }

    scores = {
        sub: [r.average_score() for r in _reviews[sub]] for sub in submissions
    }
    average_scores = {
        sub: (f'{sum(scores[sub])/len(scores[sub]):.1f}'
              if len(scores[sub]) > 0 else '-')
        for sub in submissions}

    for sub in submissions:
        _scores = scores[sub]
        for i in range(len(_scores)):
            x = _scores[i]
            _scores[i] = '-' if x == 0 else f'{x:.1f}'

    warnings = {}
    for sub in submissions:
        _w = []
        if sub.status == Submission.UNDER_REVIEW:
            if num_revs_incomplete[sub] > 0:
                _w.append(f'{num_revs_incomplete[sub]} reviews incomplete')
            if len(_reviews[sub]) < sub.stype.num_reviews:
                _w.append(
                    f'missing {sub.stype.num_reviews - _reviews[sub].count()}'
                    f' review assignments'
                )
        warnings[sub] = _w + list(sub.warnings())

    items = [{
        'object': sub,
        'title': sub.title,
        'authors': [{
            'name': pr.get_full_name(),
            'user_pk': pr.user.pk,
        } for pr in sub.get_authors_profiles()],
        'pk': sub.pk,
        'status': sub.status,  # this is needed to make `status_class` work
        'status_display': sub.get_status_display(),
        'actions': actions[sub],
        'reviews': _reviews[sub],
        'num_reviews': sub.reviews.all().count(),
        'num_reviews_required': sub.stype.num_reviews if sub.stype else 0,
        'num_incomplete_reviews': num_revs_incomplete[sub],
        'scores': scores[sub],
        'average_score': average_scores[sub],
        'warnings': warnings[sub],
    } for sub in submissions]

    items.sort(key=lambda item: item['pk'])

    context = build_paged_view_context(
        request, items, page, 'chair:submissions-pages', {'conf_pk': conf_pk}
    )
    context.update({
        'conference': conference,
        'filter_form': form,
        'conference': conference,
    })
    return render(request, 'chair/submissions/submissions_list.html',
                  context=context)


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
    if submission.status == Submission.SUBMITTED:
        submission.status = Submission.UNDER_REVIEW
        submission.save()

        # Sending an email to authors:
        for author in submission.authors.all():
            user = author.user
            profile = user.profile
            ctx = {
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'submission': submission,
                'protocol': settings.SITE_PROTOCOL,
                'domain': settings.SITE_DOMAIN,
                'deadline': conference.review_stage.end_date,
            }
            html = render_to_string('submissions/email/status_review.html', ctx)
            text = render_to_string('submissions/email/status_review.txt', ctx)
            send_mail(
                f"[DCCN'2019] Submission #{submission.pk} is under review",
                message=text,
                html_message=html,
                recipient_list=[user.email],
                from_email=settings.DEFAULT_FROM_EMAIL,
                fail_silently=False,
            )
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


#############################################################################
# CSV EXPORTS
#############################################################################
@require_GET
@chair_required
def export_csv(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    submissions = list(conference.submission_set.all().order_by('pk'))
    profs = {
        sub: Profile.objects.filter(user__authorship__submission=sub).all()
        for sub in submissions
    }

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = \
        f'attachment; filename="submissions-{timestamp}.csv"'

    writer = csv.writer(response)
    number = 1
    writer.writerow([
        '#', 'ID', 'TITLE', 'AUTHORS', 'COUNTRY', 'CORR_AUTHOR', 'CORR_EMAIL',
        'LANGUAGE', 'LINK',
    ])

    for sub in submissions:
        # noinspection PyShadowingNames
        authors = ', '.join(pr.get_full_name() for pr in profs[sub])
        countries = ', '.join(set(p.get_country_display() for p in profs[sub]))
        owner = sub.created_by
        corr_author = owner.profile.get_full_name() if owner else ''
        corr_email = owner.email if owner else ''

        if sub.review_manuscript:
            link = request.build_absolute_uri(
                reverse('submissions:download-manuscript', args=[sub.pk]))
        else:
            link = ''
        stype = sub.stype.get_language_display() if sub.stype else ''

        row = [
            number, sub.pk, sub.title, authors, countries, corr_author,
            corr_email, stype, link
        ]
        writer.writerow(row)
        number += 1

    return response
