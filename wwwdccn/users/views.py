from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils.encoding import smart_text
from django.views.decorators.http import require_GET

User = get_user_model()


@login_required
@require_GET
def search_users(request):
    # TODO: split query into words and match them all
    query = request.GET.get('q')
    users = User.objects.filter(
        Q(profile__first_name__icontains=query) |
        Q(profile__last_name__icontains=query) |
        Q(profile__first_name_rus__icontains=query) |
        Q(profile__last_name_rus__icontains=query)
    )
    data = {'users': [{
        'id': user.id,
        'first_name': user.profile.first_name,
        'last_name': user.profile.last_name,
        'first_name_rus': user.profile.first_name_rus,
        'middle_name_rus': user.profile.middle_name_rus,
        'last_name_rus': user.profile.last_name_rus,
        'affiliation': user.profile.affiliation,
        'avatar': user.profile.avatar.url if user.profile.avatar else '',
    } for user in users]}
    return JsonResponse(data)
