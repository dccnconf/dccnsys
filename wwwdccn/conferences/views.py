from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from conferences.models import Conference, SubmissionType


@require_GET
def ajax_conference_details(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return JsonResponse({
        'full_name': conference.full_name,
        'short_name': conference.short_name,
        'is_ieee': conference.is_ieee,
        'country': conference.get_country_display(),
        'city': conference.city,
        'start_date': conference.start_date,
        'close_date': conference.close_date,
        'logotype': conference.logotype.url if conference.logotype else '',
        'description': conference.description,
        'site_url': conference.site_url,
        'submission_stage': {
            'end_date': conference.submission_stage.end_date,
        }
    })


@require_GET
def ajax_submission_type_details(request, pk):
    stype = get_object_or_404(SubmissionType, pk=pk)
    return JsonResponse({
        'id': stype.pk,
        'name': stype.name,
        'conference': stype.conference.pk,
        'description': stype.description,
        'language': stype.get_language_display(),
        'latex_template': (
            stype.latex_template.url if stype.latex_template else ''),
        'num_reviews': stype.num_reviews,
        'min_num_pages': stype.min_num_pages,
        'max_num_pages': stype.max_num_pages,
        'blind_review': stype.blind_review,
        'possible_proceedings': [
            {'id': proc.pk, 'name': proc.name}
            for proc in stype.possible_proceedings.all()
        ]
    })
