from django import template
from django.db.models import Q

from review.models import Review, Decision

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
def decision_icon_class(decision):
    if decision == Decision.ACCEPT:
        return 'fas fa-vote-yea'
    elif decision == Decision.REJECT:
        return 'fas fa-ban'
    elif decision == Decision.UNDEFINED:
        return 'fas fa-question-circle'
    return ''
