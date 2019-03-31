from django import template

from submissions.models import Submission

register = template.Library()


#TODO: implement correctly!!
@register.filter('submissions')
def submissions(user):
    return Submission.objects.all()
