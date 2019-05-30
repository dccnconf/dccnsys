from django import template

from submissions.helpers import get_affiliations_of, get_countries_of
from submissions.models import Submission

register = template.Library()


@register.filter('statusclass')
def statusclass(submission):
    if submission.status == 'SUBMIT':
        if submission.review_manuscript:
            return 'text-success'
        else:
            return 'text-warning'
    elif submission.status in {'REVIEW', 'PRINT', 'PUBLISH'}:
        return 'text-info'
    elif submission.status == 'ACCEPT':
        return 'text-success'
    elif submission.status == 'REJECT':
        return 'text-danger'
    return ''


@register.filter
def affiliations(submission):
    return get_affiliations_of(submission)


@register.filter
def countries(submission):
    return get_countries_of(submission)
