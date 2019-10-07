from django import template
from django.utils import timezone

from proceedings.models import CameraReady

register = template.Library()


@register.filter
def camera_ready_set_of(submission):
    return CameraReady.objects.filter(submission=submission, active=True)


@register.filter
def any_proceedings_editable(submission):
    end_dates = [
        getattr(pt, 'final_manuscript_deadline', None) for pt in
        CameraReady.objects.filter(
            submission=submission).values_list('proc_type', flat=True)]
    end_dates = [ed for ed in end_dates if ed is not None]
    now = timezone.now()
    return any(ed > now for ed in end_dates)
