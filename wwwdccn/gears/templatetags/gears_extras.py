from django import template
from markdown import markdown

register = template.Library()


@register.filter
def md2html(text):
    return markdown(text)
