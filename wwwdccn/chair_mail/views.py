from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access
from chair_mail.forms import EmailTemplateUpdateForm
from chair_mail.models import EmailGeneralSettings, EmailTemplate
from conferences.models import Conference


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
    print(next_url)
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

    return render(request, 'chair_mail/message_template.html', context={
        'conference': conference,
        'template': mail_template,
        'form': form,
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
