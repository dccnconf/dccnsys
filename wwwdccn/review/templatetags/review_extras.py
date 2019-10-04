from django import template
from django.db.models import Q

from review.models import Review, ReviewStats, ReviewDecisionType
from review.utilities import get_average_score

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
    if string == ReviewDecisionType.ACCEPT:
        return 'success-17'
    elif string == ReviewDecisionType.REJECT:
        return 'danger-17'
    elif string == '':
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
    if score == 0 or score is None:
        return ''
    return '{:.1f}'.format(score)


@register.filter
def missing_reviews(submission):
    stage = submission.reviewstage_set.first()
    num_missing = stage.get_num_missing_reviews() if stage else 0
    return ['-' for _ in range(num_missing)]


@register.filter
def review_stage_of(submission):
    return submission.reviewstage_set.first()


@register.filter
def review_decision_of(submission):
    return getattr(review_stage_of(submission), 'decision', None)


@register.filter
def reviews_of(submission):
    stage = review_stage_of(submission)
    if stage:
        return stage.review_set.all()
    return []


@register.filter
def review_decision_is(decision, accept_or_reject):
    if not decision:
        return False
    d = decision.decision_type.decision
    query = accept_or_reject.lower()
    return (('accept' in query and d == ReviewDecisionType.ACCEPT)
            or ('reject' in query and d == ReviewDecisionType.REJECT))


@register.filter
def review_decision_color(decision):
    if not decision:
        return 'secondary'
    d = decision.decision_type.decision
    if d == ReviewDecisionType.ACCEPT:
        return 'success'
    elif d == ReviewDecisionType.REJECT:
        return 'danger'
    return 'warning'
