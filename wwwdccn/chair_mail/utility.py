from django.conf import settings
from django.http import Http404
from django.urls import reverse


def get_email_frame_or_404(conference):
    frame = get_email_frame(conference)
    if frame is None:
        raise Http404
    return frame


def get_email_frame(conference):
    if hasattr(conference, 'email_settings'):
        return conference.email_settings.frame
    return None


def get_absolute_url(url):
    url = url.lstrip()
    _url = url.lower()
    # TODO: use wildcard instead of this enumeration:
    if (_url.startswith('http://') or _url.startswith('https://') or
            _url.startswith('ftp://') or _url.startswith('mailto:') or
            _url.startswith('ssh://')):
        return url
    need_slash = not url.startswith('/')
    protocol = settings.SITE_PROTOCOL
    domain = settings.SITE_DOMAIN
    return f'{protocol}://{domain}{"/" if need_slash else ""}{url}'


def get_anchor_string(url, href_prefix=''):
    return f'<a href="{href_prefix}{url}">{url}</a>'


def get_html_ul(items, value=None, url=None):
    if not items:
        return ''

    def identity(x):
        return x

    _get_value = identity if value is None else value

    if url is None:
        list_items = [f'<li>{_get_value(item)}</li>' for item in items]
    else:
        def get_value(item):
            _val = str(_get_value(item))
            return _val if _val.strip() else url(item)

        list_items = [
            f'<li><a href="{url(item)}">{get_value(item)}</a></li>'
            for item in items
        ]

    return f'<ul>{"".join(list_items)}</ul>'


def reverse_preview_url(msg_type, conference):
    from .models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION
    kwargs = {'conf_pk': conference.pk}
    if msg_type == MSG_TYPE_USER:
        return reverse('chair_mail:render-preview-user', kwargs=kwargs)
    elif msg_type == MSG_TYPE_SUBMISSION:
        return reverse('chair_mail:render-preview-submission', kwargs=kwargs)
    raise ValueError(f'unexpected message type "{msg_type}"')


def reverse_list_objects_url(msg_type, conference):
    from .models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION
    kwargs = {'conf_pk': conference.pk}
    if msg_type == MSG_TYPE_USER:
        return reverse('chair_mail:list-users', kwargs=kwargs)
    elif msg_type == MSG_TYPE_SUBMISSION:
        return reverse('chair_mail:list-submissions', kwargs=kwargs)
    raise ValueError(f'unexpected message type "{msg_type}"')


def get_object_model(msg_type):
    from .models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION
    if msg_type == MSG_TYPE_USER:
        from users.models import User
        return User
    elif msg_type == MSG_TYPE_SUBMISSION:
        from submissions.models import Submission
        return Submission
    raise ValueError(f'unexpected message type "{msg_type}"')
