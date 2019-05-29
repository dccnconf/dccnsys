from django import template

from conferences.helpers import get_authors_of

register = template.Library()


@register.filter
def submissions_authors(conference):
    return list(get_authors_of(conference.submission_set.all()))
