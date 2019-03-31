from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from conferences.models import Conference


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
