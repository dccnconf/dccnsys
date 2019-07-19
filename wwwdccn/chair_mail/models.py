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
    text_html = models.TextField()
    text_plain = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("name", "conference"),)

    def render_html(self, title, body, signature, footer, logo_url):
        return Template(self.text_html).render({
            'title': title,
            'body': body,
            'signature': signature,
            'footer': footer,
            'conference_logo': logo_url,
            'conference_full_name': self.conference.full_name,
            'conference_short_name': self.conference.short_name,
        })

    def render_plain(self, title, body, signature, footer, logo_url):
        text_plain = self.text_plain
        if not text_plain:
            text_plain = html2text(self.text_html)
        return Template(text_plain).render({
            'title': title,
            'body': body,
            'signature': signature,
            'footer': footer,
            'conference_logo': logo_url,
            'conference_full_name': self.conference.full_name,
            'conference_short_name': self.conference.short_name,
        })


class EmailUserList(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    users = models.ManyToManyField(User)

    class Meta:
        unique_together = (("name", "conference"),)


class EmailGeneralSettings(models.Model):
    default_template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True
    )


class EmailMessage(models.Model):
    DRAFT = 'DRAFT'
    SENDING = 'TX'
    SENT = 'SENT'

    STATUS_CHOICE = (
        (DRAFT, _('Draft')),
        (SENDING, _('Sending')),
        (SENT, _('Sent'))
    )

    subject = models.CharField(max_length=1024)
    text_html = models.TextField()
    text_plain = models.TextField()
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    users_to = models.ManyToManyField(User, related_name='email_messages')
    sent_at = models.DateTimeField()

    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='sent_email_messages'
    )

    status = models.CharField(
        choices=STATUS_CHOICE,
        default=DRAFT,
        max_length=5
    )

    @staticmethod
    def create_message(subject, body_html, template, users_to, body_plain=None):
        conference = template.conference
        if body_plain is None:
            body_plain = html2text(body_html)
        message = EmailMessage(
            conference=conference,
            subject=subject,
            text_html=template.render_html(body_html),
            text_plain=template.render_plain(body_plain),
        )
        for user in users_to:
            message.users_to.add(user)
        message.save()
        return message

    def send(self, sender, context: dict, user_context=None):
        """Create a bunch of `EmailMessageInst` for each user and send them.

        The template from `html_template_string` is rendered with a given
        context plus user-specific context from `user_context[user]`. For
        each user, rendered template is put into a new `EmailMessageInst` and
        this instance is being stored and sent.

        :param sender: user that initiates message sending
        :param context: context for template rendering.
        :param user_context: `dict` with `User -> dict` items. Specific context
            for each user, e.g. link to his login page or name.
        :return:
        """
        self.status = EmailMessage.SENDING
        text_html_template = Template(self.text_html)
        subject_template = Template(self.subject)
        text_plain_template = Template(self.text_plain)
        for user in self.users_to.all():
            ctx = dict(context)
            if user_context and user in user_context:
                ctx.update(user_context[user])
            inst = EmailMessageInst(
                user_to=user,
                message=self,
                subject=subject_template.render(ctx),
                text_html=text_html_template.render(ctx),
                text_plain=text_plain_template.render(ctx),
            )
            inst.save()
            inst.send(sender)
        self.sent_at = timezone.now()
        self.status = EmailMessage.SENT


class EmailMessageInst(models.Model):
    subject = models.TextField(max_length=1024)
    text_plain = models.TextField()
    text_html = models.TextField()
    user_to = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='email_instances'
    )
    sent_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='sent_email_instances'
    )

    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE)

    def send(self, sender):
        if not self.sent:
            from_email = settings.DEFAULT_FROM_EMAIL
            send_mail(self.subject, self.text_plain, from_email, [self.user_to],
                      html_message=self.text_html)
            self.sent_at = timezone.now()
            self.sent_by = sender
            self.sent = True
            self.save()
        return self
