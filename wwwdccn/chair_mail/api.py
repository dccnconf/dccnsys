from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET

from chair.utility import validate_chair_access
from chair_mail.forms import PreviewUserMessageForm, \
    PreviewSubmissionMessageForm
from chair_mail.mailing_lists import USER_LISTS, SUBMISSION_LISTS, ALL_LISTS, \
    find_list
from conferences.models import Conference
from submissions.models import Submission
from users.models import Profile, User


def serialize_mailing_list(ml, conference):
    return {
        'name': ml.name,
        'details': ml.details,
        'type': ml.type,
        'objects': [obj.pk for obj in ml.query(conference)]
    }


def serialize_user(profile, conference):
    url = reverse('chair:user-overview', kwargs={
        'conf_pk': conference.pk, 'user_pk': profile.user_id
    })
    name_rus = f'{profile.first_name_rus} {profile.last_name_rus}'.strip()
    data = {
        'id': profile.user_id,
        'name': profile.get_full_name(),
        'url': url,
        'avatar_url': profile.avatar.url,
        'affiliation': profile.affiliation,
        'country': profile.get_country_display(),
        'city': profile.city,
        'role': profile.role,
        'degree': profile.degree,
    }
    if name_rus:
        data['name_rus'] = name_rus
    return data


def serialize_submission(submission, conference, profiles_cache=None):
    url = reverse('chair:submission-overview', kwargs={
        'conf_pk': conference.pk, 'sub_pk': submission.pk,
    })
    authors = [{
        'id': author.user_id,
        'name': (profiles_cache[author.user_id].get_full_name()
                 if profiles_cache is not None
                 else author.user.profile.get_full_name()),
    } for author in submission.authors.all()]
    data = {
        'id': submission.pk,
        'title': submission.title,
        'authors': authors,
        'url': url,
    }
    return data


@require_GET
def list_mailing_lists(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    list_type = request.GET.get('type', default='all')
    if list_type == 'user':
        lists = USER_LISTS
    elif list_type == 'submission':
        lists = SUBMISSION_LISTS
    elif list_type == 'all':
        lists = ALL_LISTS
    else:
        return JsonResponse({'error': 'invalid list type'}, status=400)
    data = {
        'type': 'mailing_list',
        'objects': [serialize_mailing_list(ml, conference) for ml in lists],
    }
    return JsonResponse(data)


@require_GET
def mailing_list_details(request, conf_pk, name):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    try:
        ml = find_list(name)
    except KeyError:
        return JsonResponse({'error': 'list not found'}, status=400)
    return JsonResponse(serialize_mailing_list(ml, conference))


@require_GET
def list_users(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    profiles = Profile.objects.all()
    data = {
        'type': 'user',
        'objects': [serialize_user(prof, conference) for prof in profiles],
    }
    return JsonResponse(data)


@require_GET
def list_submissions(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submissions = Submission.objects.filter(conference_id=conf_pk)
    profiles_cache = {
        user.pk: user.profile
        for user in User.objects.filter(authorship__submission__in=submissions)
    }
    data = {
        'type': 'submission',
        'objects': [
            serialize_submission(submission, conference, profiles_cache)
            for submission in submissions
        ]
    }
    return JsonResponse(data)


def create_preview_view(form_class):
    def handler(request, conf_pk):
        conference = get_object_or_404(Conference, pk=conf_pk)
        validate_chair_access(request.user, conference)
        form = form_class(request.GET)
        if form.is_valid():
            data = form.render_html(conference)
            print(data)
            return JsonResponse(data)
        return JsonResponse({}, status=400)
    return handler


# @require_GET
# def search_users(request, conf_pk):
#     conference = get_object_or_404(Conference, pk=conf_pk)
#     validate_chair_access(request.user, conference)
#     q = request.GET.get('q', default='')
#     words = q.split()
#
#     # In case of empty search, return nothing:
#     if not words:
#         return JsonResponse({'users': []})
#
#     profile_query = Profile.objects.all()
#     for word in words:
#         profile_query = profile_query.filter(
#             Q(first_name__icontains=word) |
#             Q(last_name__icontains=word) |
#             Q(first_name_rus__icontains=word) |
#             Q(last_name_rus__icontains=word)
#         )
#     return JsonResponse({
#         'users': [{
#             'id': profile.user_id,
#             'name': profile.get_full_name(),
#             'url': reverse(
#                 'chair:user-overview',
#                 kwargs={'conf_pk': conf_pk, 'user_pk': profile.user_id}),
#         } for profile in profile_query]
#     })
