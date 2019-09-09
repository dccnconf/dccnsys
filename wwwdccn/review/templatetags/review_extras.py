from django import template
from django.db.models import Q

from review.models import Review, Decision
from review.utilities import EXCELLENT_QUALITY, GOOD_QUALITY, \
    AVERAGE_QUALITY, POOR_QUALITY, UNKNOWN_QUALITY, get_quality, \
    get_average_score

register = template.Library()


@register.filter
def is_reviewer(user):
    return user.reviewer_set.count()


@register.filter
def count_incomplete_reviews(user):
    return Review.objects.filter(
        Q(reviewer__user=user) & Q(submitted=False)).count()


@register.filter
def decision_color_class(string):
    if string == Decision.ACCEPT:
        return 'success-17'
    elif string == Decision.REJECT:
        return 'danger-17'
    elif string == Decision.UNDEFINED or string == '':
        return 'warning-17'
    else:
        return 'secondary'


@register.filter
def volume_color_class(string):
    if string:
        return 'success-14'
    return 'warning-13'


@register.filter
def quality_of(submission):
    return get_quality(submission)


@register.filter
def quality_icon_class(quality):
    return {
        EXCELLENT_QUALITY: 'far fa-grin-stars',
        GOOD_QUALITY: 'far fa-smile',
        AVERAGE_QUALITY: 'far fa-meh',
        POOR_QUALITY: 'far fa-frown',
        UNKNOWN_QUALITY: 'fas fa-question',
    }[quality]


@register.filter
def quality_color(quality):
    return {
        EXCELLENT_QUALITY: 'success-15',
        GOOD_QUALITY: 'info-15',
        AVERAGE_QUALITY: 'warning-15',
        POOR_QUALITY: 'danger-15',
        UNKNOWN_QUALITY: 'danger-15',
    }[quality]


@register.filter
def average_score(obj):
    score = get_average_score(obj)
    if score == 0:
        return ''
    return '{:.1f}'.format(score)
