from pprint import pprint

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access
from chair_mail.context import get_user_context, USER_VARS, \
    get_conference_context, CONFERENCE_VARS, get_submission_context, \
    SUBMISSION_VARS
from chair_mail.forms import EmailFrameUpdateForm, EmailFrameTestForm, \
    EmailTemplateForm
from chair_mail.models import EmailSettings, EmailFrame, EmailTemplate, \
    EmailMessage, GroupEmailMessage
from chair_mail.utility import get_email_frame, get_email_frame_or_404
from conferences.models import Conference
from submissions.models import Submission
from users.models import User


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


@require_GET
def group_message_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(GroupEmailMessage, pk=msg_pk)
    template = msg.template
    if request.is_ajax():
        return JsonResponse({
            'body': template.body,
            'subject': template.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'users_to': list(msg.users_to.values_list('pk')),
        })
    return render(
        request, 'chair_mail/tab_pages/group_message_details.html', context={
            'conference': conference,
            'conf_pk': conference.pk,
            'msg': msg,
            'hide_tabs': True,
        })


def compose_to_user(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user_to = get_object_or_404(User, pk=user_pk)
    profile = user_to.profile
    return _compose(
        request,
        conference=conference,
        users_to=[user_to],
        dest_name=profile.get_full_name(),
        msg_type=EmailTemplate.TYPE_USER,
        context=get_conference_context(conference),
        user_context={user_to: get_user_context(user_to, conference)},
        variables=(CONFERENCE_VARS + USER_VARS)
    )


def compose_to_submission(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)
    authors = submission.authors
    users_to = User.objects.filter(pk__in=authors.values('user__pk'))

    context = {
        **get_conference_context(conference),
        **get_submission_context(submission),
    }
    pprint(context)
    user_context = {u: get_user_context(u, conference) for u in users_to}
    variables = CONFERENCE_VARS + SUBMISSION_VARS + USER_VARS

    return _compose(
        request,
        conference=conference,
        users_to=users_to,
        dest_name=f'submission #{submission.pk}',
        msg_type=EmailTemplate.TYPE_USER,
        context=context,
        user_context=user_context,
        variables=variables,
    )


def _compose(request, conference, users_to, dest_name, msg_type, context=None,
             user_context=None, variables=None):
    """Process GET and POST requests for message composing views.

    This function expects that chair access is already validated, and the
    actual users are known. Assumes that form `EmailMessageForm` is used.

    :param request:
    :param conference:
    :param users_to:
    :param dest_name:
    :param msg_type:
    :param context:
    :param user_context
    :return:
    """
    if request.method == 'POST':
        next_url = request.POST.get('next', reverse('chair:home', kwargs={
            'conf_pk': conference.pk
        }))
        form = EmailTemplateForm(
            request.POST,
            conference=conference, created_by=request.user, msg_type=msg_type
        )
        if form.is_valid():
            template = form.save()
            message = GroupEmailMessage.create(template, users_to)
            context = context if context is not None else {}
            user_context = user_context if user_context is not None else {}
            message.send(request.user, context, user_context)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        form = EmailTemplateForm()
        next_url = request.GET['next']

    variables = variables if variables is not None else {}
    return render(
        request, 'chair_mail/preview_pages/compose_message.html', context={
            'form': form,
            'conference': conference,
            'next': next_url,
            'variables': variables,
            'destination_name': dest_name,
        })


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
                  'chair_mail/preview_pages/email_message_preview.html',
                  context={
                      'conference': conference,
                      'msg': msg,
                      'next': next_url,
                  })


#############################################################################
# MESSAGE CONTEXT VARIABLES AND FUNCTIONS
#############################################################################


DEFAULT_TEMPLATE_PLAIN = """
{{ body}}

Happy conferencing,
{{ conf_short_name }} Organization Committee
Contact us: {{ conf_email }}

----
This email was generated automatically due to actions performed at {{ site_url }}.
If you received this email unintentionally, please contact us via {{ conf_email }} 
and delete this message.
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
