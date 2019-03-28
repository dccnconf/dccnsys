from django.http import Http404
from django.shortcuts import get_object_or_404

from .models import Conference


def chair_required(fn):
    def wrapper(request, pk, *args, **kwargs):
        conference = get_object_or_404(Conference, pk=pk)
        if request.user in conference.chairs.all():
            return fn(request, pk, *args, **kwargs)
        else:
            raise Http404
    return wrapper
