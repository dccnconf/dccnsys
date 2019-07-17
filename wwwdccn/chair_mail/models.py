from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template import Template
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from html2text import html2text

from conferences.models import Conference
from users.models import User


class EmailTemplate(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("name", "conference"),)

    def render(self, title, body, signature, footer, logo_url):
        return Template(self.html).render({
            'title': title,
            'body': body,
            'signature': signature,
            'footer': footer,
            'conference_logo': logo_url,
            'conference_full_name': self.conference.full_name,
            'conference_short_name': self.conference.short_name,
        })


class EmailMessageBody(models.Model):
    SUBMISSION_MESSAGE = "SUBMISSION"
    USER_MESSAGE = "USER_MESSAGE"

    name = models.CharField(max_length=1024, blank=False)
    html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=256, default=USER_MESSAGE)

    class Meta:
        unique_together = (("name", "conference", "message_type"),)


class EmailUserList(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    users = models.ManyToManyField(User)

    class Meta:
        unique_together = (("name", "conference"),)


class EmailGeneralSettings(models.Model):
    footer = models.TextField()
    signature = models.TextField()
    logo_url = models.URLField(default="", blank=True)


class EmailMessage(models.Model):
    DRAFT = 'DRAFT'
    SENDING = 'TX'
    SENT = 'SENT'

    STATUS_CHOICE = (
        (DRAFT, _('Draft')),
        (SENDING, _('Sending')),
        (SENT, _('Sent'))
    )

    subject_template_string = models.CharField(max_length=1024)
    html_template_string = models.TextField()
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    users_to = models.ManyToManyField(User)
    sent_at = models.DateTimeField()

    status = models.CharField(
        choices=STATUS_CHOICE,
        default=DRAFT,
        max_length=5
    )

    @staticmethod
    def create_message(
            template: EmailTemplate,
            body: str, title: str, footer: str, signature: str, subject: str,
            conference_logo_url: str,
            users_to: "list of User"):
        """Create an outgoing `EmailMessage`

        For instance, let `template` be a `EmailTemplate` object with the this
        `html` field value:

        ```html
        <html>
        <head>
            <title>{{ title }}</title>
        </head>
        <body>
            <table>
                <tr>
                    <td>{{ conference_logo }}</td>
                    <td>{{ conference_full_name }}</td>
                </tr>
                <tr><td><table>
                    <tr><td>{{ body }}</td></tr>
                    <tr><td>{{ signature }}</td></tr>
                </table></td></tr>
                <tr><td>{{ footer }}</td></tr>
            </table>
        </body>
        </html>
        ```

        Let `body` be specified as:

        ```html
        <p>Dear {{ first_name }} {{ last_name }},</p>

        <p>
        your submission #{{ submission_id }} "{{ submission_title }}" to
        {{ conference_short_name }} was accepted.
        </p>
        ```

        Signature:

        ```html
        <p>With kind regards,</p>
        <p>{{ conference_short_name }} Organizers, {{ conference_email }}</p>
        <p>{{ conference_site_url }}</p>
        ```

        Let `footer` contain:

        ```html
        <p>This email was automatically generated. If you do not want to receive
        these messages anymore, please, contact us {{ conference_email }}</p>.
        ```

        Let subject line look like:

        ```
        [conference_short_name] Submission #{{ submission_id }}`accepted
        ```

        And `title = 'Submission #{{ submission_id }} was accepted!'`

        Then in the result `EmailMessage` field `html_template_string` will be:

       ```html
        <html>
        <head>
            <title>Submission #{{ submission_id }} was accepted!</title>
        </head>
        <body>
            <table>
                <tr>
                    <td>http://some.cloud/conference_logo.png</td>
                    <td>My Favourite Conference</td>
                </tr>
                <tr><td><table>
                    <tr><td>
        <p>Dear {{ first_name }} {{ last_name }},</p>

        <p>your submission #{{ submission_id }} "{{ submission_title }}" to
        {{ conference_short_name }} was accepted.</p>
                    </td></tr>
        <p>With kind regards,</p>
        <p>{{ conference_short_name }} Organizers, {{ conference_email }}</p>
        <p>{{ conference_site_url }}</p>
                    <tr><td>
                    </td></tr>
                </table></td></tr>
                <tr><td>
        <p>This email was automatically generated. If you do not want to receive
        these messages anymore, please, contact us {{ conference_email }}</p>
                </td></tr>
            </table>
        </body>
        </html>
        ```

        Field `subject_template_string` will be equal to `subject`.

        > Note that variables inside `body`, `title`, `footer`, `signature` or
        `subject` **are not assigned** in this call, they will be assigned
         later in `send()` call. Only variables in `template.html` are
         assigned here.

        :param template: message template with `title`, `body`, `footer`,
            'conference_logo', 'conference_full_name', 'conference_short_name'
             and `signature` parameters, instance of `EmailTemplate`.
        :param body: the message body template. May contain any variables those
            will be filled in further `send()` call. This field can be filled
            from `EmailMessageBody.html` field value.
        :param title: the message title template. May also contain the same
            variables as `body`.
        :param footer: the message footer template. May contain the same
            variables as `body`.
        :param signature: the message signature template. May contain the same
            variables as `body`.
        :param subject: message subject template. May contain the same
            variables as `body`.
        :param conference_logo_url: a URL to a conference logotype. Please,
            provide public access URLs (e.g., on some cloud).
        :param users_to: a list of `User` objects who will receive the message.
        :return: `EmailMessage` object.
        """
        conference = template.conference
        message = EmailMessage(conference=conference)
        message.html_template_string = template.render(
            title=title, body=body, signature=signature, footer=footer,
            logo_url=conference_logo_url
        )
        for user in users_to:
            message.users_to.add(user)
        message.subject_template_string = subject
        message.save()
        return message

    def send(self, context: dict, user_context=None):
        """Create a bunch of `EmailMessageInst` for each user and send them.

        The template from `html_template_string` is rendered with a given
        context plus user-specific context from `user_context[user]`. For
        each user, rendered template is put into a new `EmailMessageInst` and
        this instance is being stored and sent.

        :param context: context for template rendering.
        :param user_context: `dict` with `User -> dict` items. Specific context
            for each user, e.g. link to his login page or name.
        :return:
        """
        self.status = EmailMessage.SENDING
        html_template = Template(self.html_template_string)
        subj_template = Template(self.subject_template_string)
        for user in self.users_to.all():
            ctx = dict(context)
            if user_context and user in user_context:
                ctx.update(user_context[user])
            inst = EmailMessageInst(user_to=user, message=self)
            inst.subject = subj_template.render(ctx)
            html = html_template.render(ctx)
            inst.html = html
            inst.text = html2text(html)
            inst.save()
            inst.send()
        self.sent_at = timezone.now()
        self.status = EmailMessage.SENT


class EmailMessageInst(models.Model):
    subject = models.TextField(max_length=1024)
    text = models.TextField()
    html = models.TextField()
    user_to = models.ForeignKey(User, on_delete=models.CASCADE)
    sent_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE)

    def send(self):
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(self.subject, self.text, from_email, [self.user_to],
                  html_message=self.html)
        self.sent_at = timezone.now()
        self.sent = True
        self.save()
        return self
