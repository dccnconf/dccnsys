from django import template

from submissions.helpers import get_affiliations_of, get_countries_of

register = template.Library()


@register.filter('status_class')
def status_class(submission):
    try:
        status = submission.status
        warnings = submission.warnings()
    except AttributeError:
        status = submission['status']
        warnings = submission['warnings']

    if status == 'SUBMIT':
        return 'text-success' if not warnings else 'text-warning'
    elif status in {'REVIEW', 'PRINT', 'PUBLISH'}:
        return 'text-info'
    elif status == 'ACCEPT':
        return 'text-success'
    elif status == 'REJECT':
        return 'text-danger'
    return ''


@register.filter
def affiliations(submission):
    return get_affiliations_of(submission)


@register.filter
def countries(submission):
    return get_countries_of(submission)
