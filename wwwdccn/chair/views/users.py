import csv
from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Value, CharField, Case, When, IntegerField, \
    Count, Q
from django.db.models.functions import Concat
from django.http import Http404, HttpResponseServerError, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET

from chair.forms import FilterProfilesForm
from conferences.utilities import validate_chair_access
from chair_mail.models import EmailMessage
from conferences.models import Conference
from submissions.models import Submission
from users.models import User, Profile


@require_GET
def list_users(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    profiles = Profile.objects.all()
    form = FilterProfilesForm(request.GET, instance=conference)
    if form.is_valid():
        profiles = form.apply(profiles)

    pks = profiles.values_list('user_id', flat=True)
    paginator = Paginator(pks, settings.ITEMS_PER_PAGE)
    page = paginator.page(request.GET.get('page', 1))

    context = {
        'conference': conference,
        'filter_form': form,
        'page': page,
    }
    return render(request, 'chair/users/list.html', context=context)


@require_GET
def feed_item(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    profile = Profile.objects.filter(user_id=user_pk).annotate(
        num_reviewers=Count('user__reviewer', filter=Q(
            user__reviewer__conference=conf_pk))
    ).annotate(
        full_name_rus=Concat(
            'last_name_rus', Value(' '), 'first_name_rus', Value(' '),
            'middle_name_rus', output_field=CharField()),
        is_reviewer=Case(
            When(num_reviewers__gt=0, then=Value(1)),
            default=Value(0), output_field=IntegerField()),
        num_reviews=Count('user__reviewer__reviews__pk', filter=Q(
            user__reviewer__reviews__paper__conference=conf_pk), distinct=True),
        num_incomplete_reviews=Count('user__reviewer__reviews__pk', filter=Q(
            user__reviewer__reviews__paper__conference=conf_pk,
            user__reviewer__reviews__submitted=False
        ), distinct=True),
        num_submissions=Count('user__authorship', filter=Q(
            user__authorship__submission__conference=conf_pk
        ), distinct=True)
    ).first()

    if not profile:
        raise Http404

    list_view_url = request.GET.get(
        'list_view_url', reverse('chair:users', kwargs={'conf_pk': conf_pk}))

    return render(request, 'chair/users/feed/card.html', {
        'profile': profile,
        'list_view_url': list_view_url,
        'conference': conference,
    })


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


@require_GET
def export_csv(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    form = FilterProfilesForm(request.GET, instance=conference)
    if not form.is_valid():
        return HttpResponseServerError()

    # Prepare additional columns:
    profiles = form.apply(Profile.objects.all()).annotate(
        num_submissions=Count('user__authorship', filter=Q(
            user__authorship__submission__conference=conference
        ), distinct=True)).annotate(
        num_accepted_submissions=Count('user__authorship', filter=Q(
            user__authorship__submission__conference=conference,
            user__authorship__submission__status=Submission.ACCEPTED
        ), distinct=True)).distinct()

    # Create the HttpResponse object with the appropriate header.
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = \
        f'attachment; filename="users-{timestamp}.csv"'
    writer = csv.writer(response)

    # import sys
    # writer = csv.writer(sys.stdout)
    writer.writerow(form.cleaned_data['columns'])

    for order, pr in enumerate(list(profiles)):
        record = {
            form.ORDER_COLUMN: order + 1,
            form.ID_COLUMN: pr.user_id,
            form.FULL_NAME_COLUMN: f'{pr.last_name} {pr.first_name}',
            form.FULL_NAME_RUS_COLUMN: ' '.join((
                pr.last_name_rus, pr.first_name_rus, pr.middle_name_rus)),
            form.DEGREE_COLUMN: pr.get_degree_display(),
            form.COUNTRY_COLUMN: pr.get_country_display(),
            form.CITY_COLUMN: pr.city,
            form.AFFILIATION_COLUMN: pr.affiliation,
            form.ROLE_COLUMN: pr.get_role_display(),
            form.EMAIL_COLUMN: pr.email,
            form.NUM_SUBMITTED_COLUMN: pr.num_submissions,
            form.NUM_ACCEPTED_COLUMN: pr.num_accepted_submissions,
            form.IEEE_MEMBER_COLUMN: 'IEEE Member' if pr.ieee_member else '',
            form.STUDENT_COLUMN: 'Student' if pr.is_student() else '',
        }
        row = []
        for col in form.cleaned_data['columns']:
            row.append(record[col])
        writer.writerow(row)

    return response


def compose_redirect(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    form = FilterProfilesForm(request.GET, instance=conference)
    if not form.is_valid():
        return HttpResponseServerError()

    users = form.apply(Profile.objects.all()).values_list('user_id', flat=True)
    base_url = reverse('chair_mail:compose-user', kwargs={'conf_pk': conf_pk})
    query_string = urlencode({
        'objects': ','.join(str(pk) for pk in users),
        'next': request.GET.get('next', reverse(
            'chair:users', kwargs={'conf_pk': conf_pk}))
    })
    url = f'{base_url}?{query_string}'
    print(url)
    return redirect(url)
