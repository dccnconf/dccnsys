from django import template
from markdown import markdown

register = template.Library()


@register.filter
def md2html(text):
    return markdown(text)


@register.simple_tag
def update_param(request, clear_keys='', **kwargs):
    items = []
    keys_to_remove = [key.strip().lower() for key in clear_keys.split(',')]
    for key in request.GET:
        if key in keys_to_remove:
            continue
        value = kwargs.get(key, request.GET.getlist(key))
        # Django groups values of multiple select into list of values
        # within a single key; however, in the query string we need to expand
        # it:
        if value is not None:
            if isinstance(value, list):
                items.extend([f'{key}={item}' for item in value])
            else:
                items.append(f'{key}={value}')
    # Append all keys not found in request.GET, but passed in kwargs:
    for name in [key for key in kwargs if
                 key not in request.GET and key not in keys_to_remove]:
        items.append(f'{name}={kwargs[name]}')
    return '&'.join(items)


@register.filter
def get_item(d, key):
    return d.get(key)
