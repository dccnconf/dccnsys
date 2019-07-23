from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template import Template, Context
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from html2text import html2text

from conferences.models import Conference
from users.models import User


class EmailTemplate(models.Model):
    text_html = models.TextField()
    text_plain = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    @staticmethod
    def render_message_template(message_template, conference, subject, body):
        return Template(message_template).render(Context({
            'subject': subject,
            'body': body,
            'conf_email': conference.contact_email,
            'conf_logo': "",
            'conf_full_name': conference.full_name,
            'conf_short_name': conference.short_name,
        }, autoescape=False))

    def render_html(self, subject, body):
        return EmailTemplate.render_message_template(
            self.text_html, self.conference, subject, body
        )

    def render_plain(self, subject, body):
        text_plain = self.text_plain
        if not text_plain:
            text_plain = html2text(self.text_html)
        return EmailTemplate.render_message_template(
            text_plain, self.conference, subject, body
        )


class EmailUserList(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    users = models.ManyToManyField(User)

    class Meta:
        unique_together = (("name", "conference"),)


class EmailGeneralSettings(models.Model):
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True
    )
    conference = models.OneToOneField(
        Conference, null=True, blank=True, on_delete=models.CASCADE,
        related_name='mail_settings',
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
    sent_at = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(blank=True, max_length=128)

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
    def create_message(subject, body_html, email_template, users_to,
                       body_plain=None, message_type=''):
        assert isinstance(email_template, EmailTemplate)
        conference = email_template.conference
        if body_plain is None:
            body_plain = html2text(body_html)
        message = EmailMessage.objects.create(
            conference=conference,
            subject=subject,
            text_html=email_template.render_html(subject, body_html),
            text_plain=email_template.render_plain(subject, body_plain),
            message_type=message_type,
        )
        for user in users_to:
            message.users_to.add(user)
        message.save()
        return message

    def send(self, sender, context=None, user_context=None):
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
            ctx = dict(context) if context is not None else {}
            if user_context and user in user_context:
                ctx.update(user_context[user])
            ctx = Context(ctx)
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
    sent_at = models.DateTimeField(auto_now_add=True)
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
