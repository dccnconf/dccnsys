from django import template


register = template.Library()


@register.filter
def is_student(profile):
    return profile.role in ('Student', 'PhD Student')
