from functools import wraps

from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access, build_paged_view_context
from conferences.models import Conference
from review.forms import UpdateVolumeForm
from submissions.models import Submission


def require_chair(fn):
    @wraps(fn)
    def wrapper(request, conf_pk, *args, **kwargs):
        conference = get_object_or_404(Conference, pk=conf_pk)
        validate_chair_access(request.user, conference)
        return fn(request, conference, *args, **kwargs)
    return wrapper


@require_GET
@require_chair
def papers_list(request, conference, page=1):
    submissions_pks = Submission.objects.filter(
        Q(conference=conference) & Q(status__in=[
            Submission.ACCEPTED, Submission.IN_PRINT, Submission.PUBLISHED])
    ).distinct().order_by('pk').values_list('pk', flat=True)

    context = build_paged_view_context(
        request, submissions_pks, page, 'chair:accepted-papers-pages',
        {'conf_pk': conference.pk})
    context.update({'conference': conference})

    return render(request, 'chair/accepted_papers/papers_list.html', context)


@require_GET
@require_chair
def feed_item(request, conference, sub_pk):
    submission = get_object_or_404(Submission, pk=sub_pk)
    return render(request, 'chair/accepted_papers/_feed_item.html', {
        'conf_pk': conference.pk,
        'submission': submission,
        'decision': submission.review_decision.first(),
        'form_data': _get_volume_form_data(submission),
    })


def volume_control_panel(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.get(pk=sub_pk)
    decision = submission.review_decision.first()
    form = UpdateVolumeForm(request.POST or None, instance=decision)
    if request.method == 'POST' and form.is_valid():
        form.save()
    return render(request, 'chair/accepted_papers/_feed_item.html', {
        'conf_pk': conference.pk,
        'submission': submission,
        'decision': submission.review_decision.first(),
        'form_data': _get_volume_form_data(submission),
    })


@require_POST
def commit_volume(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.get(pk=sub_pk)
    decision = submission.review_decision.first()
    decision.commit()
    return render(request, 'chair/accepted_papers/_feed_item.html', {
        'conf_pk': conference.pk,
        'submission': submission,
        'decision': submission.review_decision.first(),
        'form_data': _get_volume_form_data(submission),
    })


def _get_volume_form_data(submission):
    decision = submission.review_decision.first()
    proc_type = decision.proc_type
    volume = decision.volume if decision else None
    default_option = [('', 'Not selected')]

    data_volume = {
        'hidden': False,
        'value': '', 'display': default_option[0][-1],
        'options': default_option + [
            (vol.pk, vol.name) for vol in proc_type.volumes.all()],

    }
    if volume:
        data_volume.update({'value': volume.pk, 'display': volume.name})
    return {
        'volume': data_volume,
        'committed': decision.committed if decision else True
    }
