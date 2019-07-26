from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_GET, require_POST
from html2text import html2text

from chair.utility import validate_chair_access
from chair_mail.forms import EmailTemplateUpdateForm, EmailTemplateTestForm, \
    EmailMessageForm
from chair_mail.models import EmailGeneralSettings, EmailTemplate, EmailMessage, \
    EmailMessageInst
from conferences.models import Conference
from submissions.models import Submission
from users.models import User


def get_mail_template_or_404(conference):
    if hasattr(conference, 'mail_settings'):
        mail_template = conference.mail_settings.template
        if mail_template is not None:
            return mail_template
    raise Http404


@require_GET
def overview(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    if hasattr(conference, 'mail_settings'):
        mail_settings = conference.mail_settings
        mail_template = mail_settings.template
    else:
        mail_template = None

    template_exists = mail_template is not None

    if template_exists:
        template_html = mail_template.text_html
        template_plain = mail_template.text_plain
    else:
        template_html = ""
        template_plain = ""

    return render(request, 'chair_mail/overview.html', context={
        'conference': conference,
        'template': mail_template,
        'template_html': template_html,
        'template_plain': template_plain,
    })


@require_POST
def create_template(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    if not hasattr(conference, 'mail_settings'):
        EmailGeneralSettings.objects.create(conference=conference)
        messages.success(request, 'Created email general settings')
    mail_settings = conference.mail_settings
    template = mail_settings.template
    if template:
        template.text_html = DEFAULT_TEMPLATE_HTML
        template.text_plain = DEFAULT_TEMPLATE_PLAIN
        template.created_at = timezone.now()
        template.updated_at = timezone.now()
        template.created_by = request.user
        template.save()
        messages.success(request, 'Reset existing template')
    else:
        template = EmailTemplate.objects.create(
            conference=conference,
            created_by=request.user,
            text_plain=DEFAULT_TEMPLATE_PLAIN,
            text_html=DEFAULT_TEMPLATE_HTML,
        )
        mail_settings.template = template
        mail_settings.save()
        messages.success(request, 'Created new template')

    next_url = request.GET.get(
        'next',
        reverse('chair_mail:overview', kwargs={'conf_pk': conf_pk})
    )
    return redirect(next_url)


def message_template(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    mail_template = get_mail_template_or_404(conference)

    if request.method == 'POST':
        form = EmailTemplateUpdateForm(request.POST, instance=mail_template)
        if form.is_valid():
            form.save()
            return redirect('chair_mail:message-template', conf_pk=conf_pk)
    else:
        form = EmailTemplateUpdateForm(instance=mail_template)

    return render(request, 'chair_mail/email_template.html', context={
        'conference': conference,
        'template': mail_template,
        'form': form,
    })


@require_GET
def sent_messages_list(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    email_messages = conference.emailmessage_set.all().order_by('-sent_at')
    return render(request, 'chair_mail/sent_messages_list.html', context={
        'conference': conference,
        'conf_pk': conference.pk,
        'template': get_mail_template_or_404(conference),
        'email_messages': email_messages,
    })


@require_POST
def send_template_test_message(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    form = EmailTemplateTestForm(request.POST)
    if form.is_valid():
        form.send_message(request.user, conference)
    return redirect('chair_mail:message-template', conf_pk=conf_pk)


def _compose(request, conference, users_to, dest_name, variables=None,
             ctx=None, user_ctx=None):
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
            'pk': conference.pk
        }))
        form = EmailMessageForm(request.POST)
        if form.is_valid():
            body_html = form.cleaned_data['body_html']
            body_plain = form.cleaned_data['body_plain']

            message = EmailMessage.create_message(
                subject=form.cleaned_data['subject'],
                body_html=body_html,
                body_plain=body_plain if body_plain else html2text(body_html),
                users_to=users_to,
                conference=conference,
                message_type=EmailMessage.SUBMISSION_MESSAGE,
            )

            _ctx = {}  # Provide context always being used here
            _ctx.update(ctx if ctx is not None else {})

            _user_ctx = {
                u: {
                    'first_name': u.profile.first_name,
                    'last_name': u.profile.last_name,
                    'user_pk': u.pk
                } for u in users_to
            }
            _user_ctx.update(user_ctx if user_ctx is not None else {})

            message.send(request.user, context=_ctx, user_context=_user_ctx)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        form = EmailMessageForm()
        next_url = request.GET['next']

    _vars = [
        ('first_name', _('user first name')),
        ('last_name', _('user first name')),
        ('user_pk', _('user identifier')),
    ]
    _vars.extend(variables if variables is not None else [])

    return render(request, 'chair_mail/compose_message.html', context={
        'form': form,
        'users_to': users_to,
        'conference': conference,
        'next': next_url,
        'variables': _vars,
        'destination_name': dest_name,
    })


# noinspection PyUnresolvedReferences
def compose_user_message(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user_to = get_object_or_404(User, pk=user_pk)
    profile = user_to.profile
    return _compose(request, conference, [user_to], profile.get_full_name())


# noinspection PyUnresolvedReferences
def compose_paper_message(request, conf_pk, subm_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=subm_pk)
    authors = submission.authors
    users_to = User.objects.filter(pk__in=authors.values('user__pk'))
    context = {
        'paper_title': submission.title,
        'paper_pk': submission.pk,
        'paper_url': reverse('submissions:details', kwargs={
            'pk': submission.pk
        }),
    }
    variables = [
        ('paper_title', _('title of the submission')),
        ('paper_pk', _('submission identifier')),
        ('paper_url', _('URL of the submission overview page')),
    ]
    return _compose(
        request, conference, users_to, f'submission #{subm_pk} authors',
        variables=variables, ctx=context
    )


@require_GET
def message_instance_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(EmailMessageInst, pk=msg_pk)
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
    return render(request, 'chair_mail/sent_message_instance_view.html', context={
        'conference': conference,
        'msg': msg,
        'next': next_url,
    })


@require_GET
def message_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(EmailMessage, pk=msg_pk)
    if request.is_ajax():
        print()
        return JsonResponse({
            'body_html': msg.body_html,
            'body_plain': msg.body_plain,
            'subject': msg.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'users_to': list(msg.users_to.values_list('pk')),
        })
    next_url = request.GET.get('next', default='')
    # TODO: replace template!
    return render(request, 'chair_mail/sent_message_details.html', context={
        'conference': conference,
        'conf_pk': conference.pk,
        'msg': msg,
        'next': next_url,
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
      <p>
        ----<br>
        This email was generated automatically due to actions performed at <a href="{{ site_url }}">{{ site_url }}</a>.<br>
        If you received this email unintentionally, please <a href="{{ contact_mail }}">contact us</a> and delete this message.
      </p>
    </td>
  </tr>
</table>
</body>
</html>
"""
