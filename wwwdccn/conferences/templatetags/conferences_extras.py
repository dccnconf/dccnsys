from django import template

from conferences.helpers import (
    get_authors_of, get_countries_of, get_affiliations_of,
)

register = template.Library()


@register.filter
def submissions_authors(conference):
    return list(get_authors_of(conference.submission_set.all()))


@register.filter
def countries(conference):
    return get_countries_of(conference.submission_set.all())


@register.filter
def affiliations(conference):
    return get_affiliations_of(conference.submission_set.all())
