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
        return 'success'
    elif string == Decision.REJECT:
        return 'danger'
    elif string == Decision.UNDEFINED or string == '':
        return 'warning-13'
    else:
        return 'secondary'


@register.filter
def volume_color_class(string):
    if string:
        return 'success-14'
    return 'warning-13'


@register.filter
def decision_icon_class(decision):
    if decision == Decision.ACCEPT:
        return 'fas fa-vote-yea'
    elif decision == Decision.REJECT:
        return 'fas fa-ban'
    elif decision == Decision.UNDEFINED:
        return 'fas fa-question-circle'
    return ''


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
        EXCELLENT_QUALITY: 'success',
        GOOD_QUALITY: 'info',
        AVERAGE_QUALITY: 'warning',
        POOR_QUALITY: 'danger',
        UNKNOWN_QUALITY: 'danger',
    }[quality]


@register.filter
def average_score(obj):
    score = get_average_score(obj)
    if score == 0:
        return ''
    return '{:.1f}'.format(score)
