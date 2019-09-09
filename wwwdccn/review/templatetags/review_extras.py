from django import template
from django.db.models import Q

from review.models import Review, Decision, ReviewStats
from review.utilities import get_quality, get_average_score

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
def quality_icon_class(quality):
    return {
        ReviewStats.EXCELLENT_QUALITY: 'far fa-grin-stars',
        ReviewStats.GOOD_QUALITY: 'far fa-smile',
        ReviewStats.AVERAGE_QUALITY: 'far fa-meh',
        ReviewStats.POOR_QUALITY: 'far fa-frown',
        ReviewStats.UNKNOWN_QUALITY: 'far fa-question-circle',
    }[quality]


@register.filter
def quality_of(review_stats, obj):
    return review_stats.qualify_score(get_average_score(obj))


@register.filter
def quality_color(quality):
    return {
        ReviewStats.EXCELLENT_QUALITY: 'success-15',
        ReviewStats.GOOD_QUALITY: 'info-15',
        ReviewStats.AVERAGE_QUALITY: 'warning-15',
        ReviewStats.POOR_QUALITY: 'danger-15',
        ReviewStats.UNKNOWN_QUALITY: 'danger-15',
    }[quality]


@register.filter
def average_score(obj):
    score = get_average_score(obj)
    if score == 0:
        return ''
    return '{:.1f}'.format(score)


@register.filter
def missing_reviews(submission):
    num_required = submission.stype.num_reviews if submission.stype else 0
    num_existing = submission.reviews.count()
    return ['-' for _ in range(max(num_required - num_existing, 0))]
