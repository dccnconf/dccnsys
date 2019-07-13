import csv
import functools
import logging
import math
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import ugettext_lazy as _

from chair.forms import FilterSubmissionsForm, FilterUsersForm
from conferences.decorators import chair_required
from conferences.models import Conference
from review.models import Reviewer
from submissions.models import Submission
from submissions.forms import SubmissionDetailsForm, AuthorCreateForm, \
    AuthorDeleteForm, InviteAuthorForm, AuthorsReorderForm
from users.models import Profile

ITEMS_PER_PAGE = 10


User = get_user_model()
logger = logging.getLogger(__name__)


def validate_chair_access(user, conference):
    if user not in conference.chairs.all():
        raise Http404


def _build_paged_view_context(request, items, page, viewname, kwargs):
    num_items = len(items)
    num_pages = int(math.ceil(num_items / ITEMS_PER_PAGE))

    if page < 1 or page > max(num_pages, 1):
        raise Http404

    first_index = min((page - 1) * ITEMS_PER_PAGE, num_items)
    last_index = min(page * ITEMS_PER_PAGE, num_items)
    first_page_url, last_page_url = '', ''
    prev_page_url, next_page_url = '', ''
    query_string = request.GET.urlencode()

    def _append_query_string(url):
        return url + '?' + query_string if query_string and url else url

    if page > 1:
        prev_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': page-1}))
        first_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': 1}))

    if page < num_pages:
        next_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': page+1}))
        last_page_url = reverse(
            viewname, kwargs=dict(kwargs, **{'page': num_pages}))

    page_urls = []
    for pi in range(1, num_pages + 1):
        page_urls.append(
            _append_query_string(
                reverse(viewname, kwargs=dict(kwargs, **{'page': pi}))
            )
        )

    return {
        'items': items[first_index:last_index],
        'num_items': num_items,
        'num_pages': num_pages,
        'curr_page': page,
        'prev_page_url': _append_query_string(prev_page_url),
        'next_page_url': _append_query_string(next_page_url),
        'first_page_url': _append_query_string(first_page_url),
        'last_page_url': _append_query_string(last_page_url),
        'page_urls': page_urls,
        'first_index': first_index + 1,
        'last_index': last_index,
    }


@require_GET
def dashboard(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    validate_chair_access(request.user, conference)
    return render(request, 'chair/dashboard.html', context={
        'conference': conference,
    })


@require_GET
def submissions_list(request, pk, page=1):
    conference = get_object_or_404(Conference, pk=pk)
    validate_chair_access(request.user, conference)
    form = FilterSubmissionsForm(request.GET, instance=conference)
    submissions = conference.submission_set.all()

    if form.is_valid():
        submissions = form.apply(submissions)

    auth_prs = {
        sub: Profile.objects.filter(user__authorship__submission=sub).values(
            'first_name', 'last_name', 'user__pk',
        )
        for sub in submissions
    }

    # Collect possible actions:
    actions = {
        sub: {
            'review': sub.status == Submission.SUBMITTED and not sub.warnings(),
            'revoke_review': sub.status == Submission.UNDER_REVIEW,
        }
        for sub in submissions
    }

    items = [{
        'object': sub,
        'warnings': sub.warnings(),
        'title': sub.title,
        'authors': [{
            'name': f"{profile['first_name']} {profile['last_name']}",
            'user_pk': profile['user__pk'],
        } for profile in auth_prs[sub]],
        'pk': sub.pk,
        'status': sub.status,  # this is needed to make `status_class` work
        'status_display': sub.get_status_display(),
        'actions': actions[sub],
    } for sub in submissions]

    context = _build_paged_view_context(
        request, items, page, 'chair:submissions-pages', {'pk': pk}
    )
    context.update({'conference': conference, 'filter_form': form})
    return render(request, 'chair/submissions_list.html', context=context)


# def submission_object_view(fn):
#     def wrapper(request, pk):


@require_GET
def submission_overview(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    return render(request, 'chair/submission_overview.html', context={
        'submission': submission,
        'conference': conference,
    })


def submission_metadata(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    if request.method == 'POST':
        form = SubmissionDetailsForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(request, f'Submission #{pk} updated')
    else:
        form = SubmissionDetailsForm(instance=submission)
    return render(request, 'chair/submission_metadata.html', context={
        'submission': submission,
        'conference': conference,
        'form': form,
    })


@require_GET
def submission_authors(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    return render(request, 'chair/submission_authors.html', context={
        'submission': submission,
        'conference': conference,
    })


def authors_post_view(form_class):
    """This decorator constructor is used in author editing POST-only views.
    """
    def decorator(fn):
        @require_POST
        @functools.wraps(fn)
        def wrapper(request, pk):
            submission = get_object_or_404(Submission, pk=pk)
            conference = submission.conference
            validate_chair_access(request.user, conference)
            form = form_class(submission, request.POST)
            if form.is_valid():
                form.save()
            return fn(request, pk)
        return wrapper
    return decorator


@authors_post_view(AuthorCreateForm)
def submission_author_create(request, pk):
    return redirect('chair:submission-authors', pk=pk)


@authors_post_view(AuthorDeleteForm)
def submission_author_delete(request, pk):
    return redirect('chair:submission-authors', pk=pk)


@authors_post_view(AuthorsReorderForm)
def submission_authors_reorder(request, pk):
    return redirect('chair:submission-authors', pk=pk)


def submission_author_invite(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    form = InviteAuthorForm(request.POST)
    if form.is_valid():
        form.save(request, submission)
        messages.success(request, _('Invitation sent'))
    else:
        messages.warning(request, _('Error sending invitation'))
    return redirect('chair:submission-authors', pk=pk)


@require_POST
def start_review(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    if submission.status == Submission.SUBMITTED:
        submission.status = Submission.UNDER_REVIEW
        submission.save()
    return redirect(request.GET.get('next', ''))


@require_POST
def revoke_review(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    if submission.status == Submission.UNDER_REVIEW:
        submission.status = Submission.SUBMITTED
        submission.save()
    return redirect(request.GET.get('next', ''))


def select_reviewers(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    conference = submission.conference
    validate_chair_access(request.user, conference)
    return render(request, 'chair/select_reviewers.html', context={
        'submission': submission,
    })


@require_GET
def users_list(request, pk, page=1):
    conference = get_object_or_404(Conference, pk=pk)
    validate_chair_access(request.user, conference)
    users = User.objects.all()
    form = FilterUsersForm(request.GET, instance=conference)

    if form.is_valid():
        users = form.apply(users)

    profiles = {user: user.profile for user in users}
    authors = {
        user: list(user.authorship.filter(submission__conference=conference))
        for user in users
    }

    items = [{
        'pk': user.pk,
        'name': profile.get_full_name(),
        'name_rus': profile.get_full_name_rus(),
        'avatar': profile.avatar,
        'country': profile.country,
        'city': profile.city,
        'affiliation': profile.affiliation,
        'degree': profile.degree,
        'role': profile.role,
        'num_submissions': len(authors[user]),
        'is_participant': len(authors[user]) > 0,
    } for user, profile in profiles.items()]

    context = _build_paged_view_context(
        request, items, page, 'chair:users-pages', {'pk': pk}
    )
    context.update({'conference': conference, 'filter_form': form})
    return render(request, 'chair/users_list.html', context=context)


@require_GET
def user_details(request, pk, user_pk):
    conference = get_object_or_404(Conference, pk=pk)
    validate_chair_access(request.user, conference)
    user = get_object_or_404(User, pk=user_pk)
    return render(request, 'chair/user_details.html', context={
        'conference': conference,
        'member': user,
        'next_url': request.GET.get('next', ''),
    })


@require_GET
def reviewers_list(request, pk, page=1):
    conference = get_object_or_404(Conference, pk=pk)
    validate_chair_access(request.user, conference)
    users = User.objects.all()
    form = FilterUsersForm(request.GET, instance=conference)

    if form.is_valid():
        users = form.apply(users)

    profiles = {user: user.profile for user in users}
    reviewers = {
        user: list(user.reviewer_set.filter(conference=conference))
        for user in users
    }
    num_reviews = {
        user: len(reviewers[user][0].reviews.all()) if reviewers[user] else 0
        for user in users
    }

    items = [{
        'pk': user.pk,
        'name': profile.get_full_name(),
        'name_rus': profile.get_full_name_rus(),
        'avatar': profile.avatar,
        'country': profile.get_country_display(),
        'city': profile.city,
        'affiliation': profile.affiliation,
        'degree': profile.degree,
        'role': profile.role,
        'invited': len(reviewers[user]) > 0,
        'num_reviews': num_reviews[user],
    } for user, profile in profiles.items()]

    context = _build_paged_view_context(
        request, items, page, 'chair:reviewers-pages', {'pk': pk}
    )
    context.update({'conference': conference, 'filter_form': form})
    return render(request, 'chair/reviewers_list.html', context=context)


@require_POST
def invite_reviewer(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user = get_object_or_404(User, pk=user_pk)
    if user.reviewer_set.count() == 0:
        Reviewer.objects.create(user=user, conference=conference)
    return redirect(request.GET.get('next'))


@require_POST
def revoke_reviewer(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user = get_object_or_404(User, pk=user_pk)
    if user.reviewer_set.count() > 0:
        Reviewer.objects.filter(user=user, conference=conference).delete()
    return redirect(request.GET.get('next'))


#############################################################################
# AJAX PARTIAL HTML
#############################################################################
@require_GET
def get_submission_overview(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    validate_chair_access(request.user, submission.conference)
    return render(request, 'chair/components/submission_overview_modal.html',
                  context={'submission': submission})


#############################################################################
# CSV EXPORTS
#############################################################################
@chair_required
@require_GET
def get_submissions_csv(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
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


@chair_required
@require_GET
def get_authors_csv(request, pk):
    conference = get_object_or_404(Conference, pk=pk)

    users = {
        user: list(user.authorship.filter(
            submission__conference=conference
        ).order_by('pk')) for user in User.objects.all()
    }

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = \
        f'attachment; filename="authors-{timestamp}.csv"'

    writer = csv.writer(response)
    number = 1
    writer.writerow([
        '#', 'ID', 'FULL_NAME', 'FULL_NAME_RUS', 'DEGREE', 'COUNTRY', 'CITY',
        'AFFILIATION', 'ROLE', 'EMAIL'
    ])

    for user in users:
        prof = user.profile
        row = [
            number, user.pk, prof.get_full_name(), prof.get_full_name_rus(),
            prof.degree, prof.get_country_display(), prof.city,
            prof.affiliation, prof.role, user.email,
        ]
        writer.writerow(row)
        number += 1

    return response
