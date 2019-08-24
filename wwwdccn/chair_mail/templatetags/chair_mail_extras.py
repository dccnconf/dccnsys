from django import template

from chair_mail.models import get_message_leaf_model

register = template.Library()


@register.filter
def msgtype(group_msg):
    return get_message_leaf_model(group_msg).message_type
