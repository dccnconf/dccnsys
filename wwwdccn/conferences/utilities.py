from django.http import Http404


def validate_chair_access(user, conference):
    if user not in conference.chairs.all():
        raise Http404
