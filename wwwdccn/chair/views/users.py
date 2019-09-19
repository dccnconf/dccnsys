from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Value, CharField, Case, When, IntegerField, \
    Count, Q
from django.db.models.functions import Concat
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from chair.forms import FilterUsersForm
from conferences.utilities import validate_chair_access
from chair_mail.models import EmailMessage
from conferences.models import Conference
from review.models import Reviewer
from users.models import User, Profile


@require_GET
def list_users(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    form = FilterUsersForm(request.GET, instance=conference)
    users = User.objects.all()

    pks = users.values_list('pk', flat=True)
    paginator = Paginator(pks, settings.ITEMS_PER_PAGE)
    page = paginator.page(request.GET.get('page', 1))

    context = {
        'conference': conference,
        'filter_form': form,
        'page': page,
    }
    return render(request, 'chair/users/list.html', context=context)

    # TODO: unlock this:
    # if form.is_valid():
    #     users = form.apply(users)

    # TODO: cut this:
    # profiles = {user: user.profile for user in users}
    # authors = {
    #     user: list(user.authorship.filter(submission__conference=conference))
    #     for user in users
    # }
    #
    # reviewers = {
    #     user: list(user.reviewer_set.filter(conference=conference))
    #     for user in users
    # }
    # num_reviews = {
    #     user: len(reviewers[user][0].reviews.all()) if reviewers[user] else 0
    #     for user in users
    # }
    # num_submitted_reviews = {
    #     user: (
    #         len(reviewers[user][0].reviews.filter(submitted=True))
    #         if reviewers[user] else 0
    #     ) for user in users
    # }
    # num_incomplete_reviews = {
    #     user: (
    #         len(reviewers[user][0].reviews.filter(submitted=False))
    #         if reviewers[user] else 0
    #     ) for user in users
    # }
    #
    # items = [{
    #     'pk': user.pk,
    #     'name': profile.get_full_name(),
    #     'name_rus': profile.get_full_name_rus(),
    #     'avatar': profile.avatar,
    #     'country': profile.get_country_display(),
    #     'city': profile.city,
    #     'affiliation': profile.affiliation,
    #     'degree': profile.degree,
    #     'role': profile.role,
    #     'num_submissions': len(authors[user]),
    #     'is_participant': len(authors[user]) > 0,
    #     'num_reviews': num_reviews[user],
    #     'num_submitted_reviews': num_submitted_reviews[user],
    #     'num_incomplete_reviews': num_incomplete_reviews[user],
    #     'is_reviewer': len(reviewers[user]) > 0,
    # } for user, profile in profiles.items()]
    #
    # items.sort(key=lambda x: x['pk'])
    # paginator = Paginator(items, settings.ITEMS_PER_PAGE)
    # page = paginator.page(request.GET.get('page', 1))
    #
    # context = {
    #     'conference': conference,
    #     'filter_form': form,
    #     'page': page,
    # }
    # return render(request, 'chair/users/list.html', context=context)


@require_GET
def feed_item(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    profile = Profile.objects.filter(user_id=user_pk).annotate(
        num_reviewers=Count('user__reviewer', filter=Q(
            user__reviewer__conference=conf_pk))
    ).annotate(
        full_name_rus=Concat(
            'first_name_rus', Value(' '), 'middle_name_rus', Value(' '),
            'last_name_rus', output_field=CharField()),
        is_reviewer=Case(
            When(num_reviewers__gt=0, then=Value(1)),
            default=Value(0), output_field=IntegerField()),
        num_reviews=Count('user__reviewer__reviews__pk', filter=Q(
            user__reviewer__reviews__paper__conference=conf_pk)),
        num_incomplete_reviews=Count('user__reviewer__reviews__pk', filter=Q(
            user__reviewer__reviews__paper__conference=conf_pk,
            user__reviewer__reviews__submitted=False
        )),
        num_submissions=Count('user__authorship', filter=Q(
            user__authorship__submission__conference=conf_pk
        ))
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
