from django import template

from chair_mail.models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION

register = template.Library()


@register.filter
def msgtype(group_msg):
    if hasattr(group_msg, 'usermessage'):
        return MSG_TYPE_USER
    elif hasattr(group_msg, 'submissionmessage'):
        return MSG_TYPE_SUBMISSION
    return ''
