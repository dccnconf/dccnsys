import csv
import logging
import math
import time
from datetime import datetime

from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from chair.forms import FilterSubmissionsForm, FilterUsersForm
from conferences.decorators import chair_required
from conferences.helpers import is_author
from conferences.models import Conference


ITEMS_PER_PAGE = 10


User = get_user_model()
logger = logging.getLogger(__name__)


@chair_required
@require_GET
def dashboard(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return render(request, 'chair/dashboard.html', context={
        'conference': conference,
    })


@chair_required
@require_GET
def submissions_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    form = FilterSubmissionsForm(request.GET, instance=conference)
    submissions = list(conference.submission_set.all())

    if form.is_valid():
        submissions = form.apply(submissions)

    return render(request, 'chair/submissions_list.html', context={
        'conference': conference,
        'submissions': submissions,
        'filter_form': form,
    })


@chair_required
@require_GET
def users_list(request, pk):
    t0 = time.time()
    conference = get_object_or_404(Conference, pk=pk)
    t01 = time.time()
    users = User.objects.all()
    t02 = time.time()
    form = FilterUsersForm(request.GET, instance=conference)
    t03 = time.time()

    if form.is_valid():
        users = form.apply(users)

    t1 = time.time()
    profiles = {user: user.profile for user in users}
    authors = {
        user: list(user.authorship.filter(submission__conference=conference))
        for user in users
    }

    t2 = time.time()
    ups = [{
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

    t3 = time.time()
    ret = render(request, 'chair/users_list.html', context={
        'conference': conference,
        'users': ups,
        'filter_form': form,
    })
    t4 = time.time()
    print('**** handling chair:users_list():')
    print(f'* getting conference, user and form took {t1 - t0:.5f} ('
          f'{t01 - t0:.5f}, {t02 - t01:.5f}, {t03 - t02:.5f}, {t1 - t03:.5f})')
    print(f'* building profiles and authors dicts took {t2 - t1:.5f}')
    print(f'* building ups list took {t3 - t2:.5f}')
    print(f'* rendering took {t4 - t3:.5f}')
    return ret


@chair_required
@require_GET
def user_details(request, pk, user_pk):
    conference = get_object_or_404(Conference, pk=pk)
    user = get_object_or_404(User, pk=user_pk)
    return render(request, 'chair/user_details.html', context={
        'conference': conference,
        'member': user,
    })


#############################################################################
# CSV EXPORTS
#############################################################################
@chair_required
@require_GET
def get_submissions_csv(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    submissions = list(conference.submission_set.all().order_by('pk'))

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
        authors = ', '.join(a.user.profile.get_full_name()
                           for a in sub.authors.all())
        countries = ', '.join(set(a.user.profile.get_country_display()
                             for a in sub.authors.all()))
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
    users = [u for u in User.objects.all().order_by('pk')
             if is_author(conference, u)]

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
            prof.degree, prof.get_country_display(), prof.city, prof.affiliation,
            prof.role, user.email,
        ]
        writer.writerow(row)
        number += 1

    return response
