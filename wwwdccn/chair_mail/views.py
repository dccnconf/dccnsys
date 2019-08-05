from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access
from chair_mail.forms import EmailFrameUpdateForm, EmailFrameTestForm, \
    EmailTemplateForm
from chair_mail.models import EmailSettings, EmailFrame, EmailTemplate, \
    EmailMessage, GroupEmailMessage
from conferences.models import Conference
from submissions.models import Submission
from users.models import User


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


def get_anchor_string(url):
    return f'<a href="{url}">{url}</a>'


@require_GET
def overview(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame(conference)
    return render(request, 'chair_mail/tab_pages/overview.html', context={
        'conference': conference,
        'frame': frame,
        'active_tab': 'overview',
    })


@require_POST
def create_frame(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    if not hasattr(conference, 'email_settings'):
        EmailSettings.objects.create(conference=conference)
        messages.success(request, 'Created email settings')
    email_settings = conference.email_settings
    frame = email_settings.frame
    if frame:
        frame.text_html = DEFAULT_TEMPLATE_HTML
        frame.text_plain = DEFAULT_TEMPLATE_PLAIN
        frame.created_at = timezone.now()
        frame.updated_at = timezone.now()
        frame.created_by = request.user
        frame.save()
        messages.success(request, 'Reset existing frame')
    else:
        frame = EmailFrame.objects.create(
            conference=conference,
            created_by=request.user,
            text_plain=DEFAULT_TEMPLATE_PLAIN,
            text_html=DEFAULT_TEMPLATE_HTML,
        )
        email_settings.frame = frame
        email_settings.save()
        messages.success(request, 'Created new template')

    default_next = reverse('chair_mail:overview', kwargs={'conf_pk': conf_pk})
    next_url = request.GET.get('next', default_next)
    return redirect(next_url)


def frame_details(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame_or_404(conference)

    if request.method == 'POST':
        form = EmailFrameUpdateForm(request.POST, instance=frame)
        if form.is_valid():
            form.save()
            return redirect('chair_mail:frame-details', conf_pk=conf_pk)
    else:
        form = EmailFrameUpdateForm(instance=frame)

    return render(request, 'chair_mail/tab_pages/frame_details.html', context={
        'conference': conference,
        'frame': frame,
        'active_tab': 'frame',
        'form': form,
    })


@require_GET
def sent_messages(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame(conference)
    msg_list = conference.sent_group_emails.all().order_by('-sent_at')
    return render(request, 'chair_mail/tab_pages/sent_messages.html', context={
        'conference': conference,
        'active_tab': 'messages',
        'frame': frame,
        'msg_list': msg_list,
    })


@require_POST
def send_frame_test_message(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    form = EmailFrameTestForm(request.POST)
    if form.is_valid():
        form.send_message(request.user, conference)
        return JsonResponse({'email': request.user.email})
    resp = JsonResponse({'email': request.user.email})
    resp.status_code = 400
    return resp


def _compose(request, conference, users_to, dest_name, msg_type,
             variables=None, ctx=None, user_ctx=None):
    """Process GET and POST requests for message composing views.

    This function expects that chair access is already validated, and the
    actual users are known. Assumes that form `EmailMessageForm` is used.

    :param request:
    :param conference:
    :param users_to:
    :param dest_name:
    :param variables:
    :param ctx:
    :param user_ctx:
    :return:
    """
    if request.method == 'POST':
        next_url = request.POST.get('next', reverse('chair:home', kwargs={
            'conf_pk': conference.pk
        }))
        form = EmailTemplateForm(
            request.POST, conference=conference, created_by=request.user,
            msg_type=msg_type
        )
        if form.is_valid():
            template = form.save()
            message = GroupEmailMessage.create(template, users_to)
            _ctx = {}  # Provide context always being used here
            _ctx.update(ctx if ctx is not None else {})
            _user_ctx = {
                u: {
                    'first_name': u.profile.first_name,
                    'last_name': u.profile.last_name,
                    'username': u.profile.get_full_name(),
                    'user_pk': u.pk
                } for u in users_to
            }
            _user_ctx.update(user_ctx if user_ctx is not None else {})
            message.send(request.user, context=_ctx, user_context=_user_ctx)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        form = EmailTemplateForm()
        next_url = request.GET['next']

    _vars = [
        ('username', _('user full name')),
        ('first_name', _('user first name')),
        ('last_name', _('user first name')),
        ('user_pk', _('user identifier')),
    ]
    _vars.extend(variables if variables is not None else [])

    return render(request, 'chair_mail/preview_pages/compose_message.html', context={
        'form': form,
        'conference': conference,
        'next': next_url,
        'variables': _vars,
        'destination_name': dest_name,
    })


# noinspection PyUnresolvedReferences
def compose_to_user(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user_to = get_object_or_404(User, pk=user_pk)
    profile = user_to.profile
    return _compose(
        request, conference, [user_to], profile.get_full_name(),
        EmailTemplate.TYPE_USER
    )


# noinspection PyUnresolvedReferences
def compose_to_submission(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)
    authors = submission.authors
    users_to = User.objects.filter(pk__in=authors.values('user__pk'))

    paper_url = reverse('submissions:overview', kwargs={'pk': submission.pk})
    context = {
        'paper_title': submission.title,
        'paper_pk': submission.pk,
        'paper_url': get_anchor_string(get_absolute_url(paper_url)),
    }
    variables = [
        ('paper_title', _('title of the submission')),
        ('paper_pk', _('submission identifier')),
        ('paper_url', _('URL of the submission overview page')),
    ]
    return _compose(
        request, conference, users_to, f'submission #{sub_pk} authors',
        EmailTemplate.TYPE_SUBMISSION, variables=variables, ctx=context,
    )


@require_GET
def message_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(EmailMessage, pk=msg_pk)
    if request.is_ajax():
        return JsonResponse({
            'text_html': msg.text_html,
            'text_plain': msg.text_plain,
            'subject': msg.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'user_to': msg.user_to.pk,
        })
    next_url = request.GET.get('next', default='')
    return render(request,
                  'chair_mail/preview_pages/email_message_preview.html', context={
        'conference': conference,
        'msg': msg,
        'next': next_url,
    })


@require_GET
def group_message_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(GroupEmailMessage, pk=msg_pk)
    template = msg.template
    if request.is_ajax():
        print()
        return JsonResponse({
            'body': template.body,
            'subject': template.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'users_to': list(msg.users_to.values_list('pk')),
        })
    return render(request, 'chair_mail/tab_pages/group_message_details.html', context={
        'conference': conference,
        'conf_pk': conference.pk,
        'msg': msg,
        'hide_tabs': True,
    })


DEFAULT_TEMPLATE_PLAIN = """
{{ body}}

Happy conferencing,
{{ conf_short_name }} Organization Committee
Contact us: {{ conf_email }}

----
This email was generated automatically due to actions performed at {{ site_url }}.
If you received this email unintentionally, please contact us via {{ conf_email }} and delete this message.
"""

DEFAULT_TEMPLATE_HTML = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <title>{{ subject }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>

<body style="margin: 0; padding: 0;">
<table>
  <tr>
    <td>
      {{ body }}
    </td>
  </tr>
  <tr>
    <td>
      <p style="margin: 20px 0 0 10px; padding: 0;">
        Happy conferencing,<br>
        {{ conf_short_name }} Organizing Committee<br>
        Contact Us: <a href="{{ conf_email }}">{{ conf_email }}</a>
      </p>
    </td>
  </tr>

  <tr>
    <td>
      <p>
        ----
        <br>
        This email was generated automatically due to actions performed at 
        <a href="{{ site_url }}">{{ site_url }}</a>.
        <br>
        If you received this email unintentionally, please 
        <a href="{{ contact_mail }}">contact us</a> and delete this message.
      </p>
    </td>
  </tr>
</table>
</body>
</html>
"""
