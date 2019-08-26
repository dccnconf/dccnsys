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


def markdownify_link(url, text=None, href_prefix=''):
    link_text = text if text is not None else url
    link_url = f'{href_prefix}{url}'
    return f'[{link_text}]({link_url})'


def markdownify_list(items, get_item_value=None, get_item_url=None,
                     default_value=''):
    if get_item_value is None:
        get_item_value = (lambda x: x)

    def get_text(an_item):
        value = get_item_value(an_item)
        return value if value else default_value

    if get_item_url is None:
        lines = [get_text(item) for item in items]
    else:
        lines = [markdownify_link(get_item_url(item), get_text(item))
                 for item in items]
    return '\n'.join(f'- {line}' for line in lines)


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


def get_object_url(msg_type, conference, obj):
    from .models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION
    if msg_type == MSG_TYPE_USER:
        return reverse('chair:user-overview', kwargs={
            'conf_pk': conference.pk, 'user_pk': obj.pk})
    elif msg_type == MSG_TYPE_SUBMISSION:
        return reverse('chair:submission-overview', kwargs={
            'conf_pk': conference.pk, 'sub_pk': obj.pk})
    raise ValueError(f'unexpected message type "{msg_type}"')


def get_object_name(msg_type, obj):
    from .models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION
    if msg_type == MSG_TYPE_USER:
        return obj.profile.get_full_name()
    elif msg_type == MSG_TYPE_SUBMISSION:
        return obj.title
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


def send_notification_message(conference, name, recipients, sender=None):
    from .models import SystemNotification
    notif = SystemNotification.objects.get(conference=conference, name=name)
    notif.send(recipients, sender=sender)


def send_submission_status_notification_message(submission):
    from submissions.models import Submission
    from .models import SystemNotification
    status = submission.status
    if status == Submission.SUBMITTED:
        name = SystemNotification.ASSIGN_STATUS_SUBMIT
    elif status == Submission.UNDER_REVIEW:
        name = SystemNotification.ASSIGN_STATUS_REVIEW
    else:
        return
    send_notification_message(submission.conference, name, [submission])
