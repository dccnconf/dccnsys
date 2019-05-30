from django import template
from django.contrib.auth import get_user_model

from conferences.helpers import (
    get_authors_of, get_countries_of, get_affiliations_of,
)
from users.models import User

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


@register.filter
def is_author(conference, user):
    assert isinstance(user, User)
    authors = get_authors_of(conference.submission_set.all())
    return user in authors


@register.filter
def num_submissions_by(conference, user):
    assert isinstance(user, User)
    authors = [author for author in user.authorship.all()
               if author.submission.conference == conference]
    return len(authors)


@register.filter
def list_submission_by(conference, user):
    assert isinstance(user, User)
    authors = [author for author in user.authorship.all()
               if author.submission.conference == conference]
    return [author.submission for author in authors]
