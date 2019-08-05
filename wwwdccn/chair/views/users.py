import csv
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST

from chair.forms import FilterUsersForm
from chair.utility import validate_chair_access, build_paged_view_context
from chair_mail.models import EmailMessage
from conferences.decorators import chair_required
from conferences.models import Conference
from review.models import Reviewer
from users.models import User


@require_GET
def list_users(request, conf_pk, page=1):
    conference = get_object_or_404(Conference, pk=conf_pk)
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

    reviewers = {
        user: list(user.reviewer_set.filter(conference=conference))
        for user in users
    }
    num_reviews = {
        user: len(reviewers[user][0].reviews.all()) if reviewers[user] else 0
        for user in users
    }
    num_submitted_reviews = {
        user: (
            len(reviewers[user][0].reviews.filter(submitted=True))
            if reviewers[user] else 0
        ) for user in users
    }
    num_incomplete_reviews = {
        user: (
            len(reviewers[user][0].reviews.filter(submitted=False))
            if reviewers[user] else 0
        ) for user in users
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
        'num_submissions': len(authors[user]),
        'is_participant': len(authors[user]) > 0,
        'num_reviews': num_reviews[user],
        'num_submitted_reviews': num_submitted_reviews[user],
        'num_incomplete_reviews': num_incomplete_reviews[user],
        'is_reviewer': len(reviewers[user]) > 0,
    } for user, profile in profiles.items()]

    items.sort(key=lambda x: x['pk'])

    context = build_paged_view_context(
        request, items, page, 'chair:users-pages', {'conf_pk': conf_pk}
    )
    context.update({
        'conference': conference,
        'filter_form': form,
    })
    return render(request, 'chair/users/users_list.html', context=context)


@require_GET
def overview(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user = get_object_or_404(User, pk=user_pk)
    return render(request, 'chair/users/user_overview.html', context={
        'conference': conference,
        'u': user,
        'active_tab': 'overview',
    })


@require_GET
def emails(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user = get_object_or_404(User, pk=user_pk)
    email_messages = (EmailMessage.objects.filter(user_to__pk=user_pk)
                      .order_by('-sent_at'))
    return render(request, 'chair/users/user_messages.html', context={
        'conference': conference,
        'u': user,
        'email_messages': email_messages,
        'active_tab': 'messages',
    })


@require_POST
def create_reviewer(request, conf_pk, user_pk):
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
# CSV EXPORTS
#############################################################################
# noinspection PyUnusedLocal
@require_GET
@chair_required
def export_csv(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)

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

