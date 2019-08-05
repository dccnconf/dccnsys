from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template import Template, Context
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from html2text import html2text

from conferences.models import Conference
from users.models import User


class EmailFrame(models.Model):
    text_html = models.TextField()
    text_plain = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    @staticmethod
    def render(frame_template, conference, subject, body):
        return Template(frame_template).render(Context({
            'subject': subject,
            'body': body,
            'conf_email': conference.contact_email,
            'conf_logo': "",
            'conf_full_name': conference.full_name,
            'conf_short_name': conference.short_name,
        }, autoescape=False))

    def render_html(self, subject, body):
        return EmailFrame.render(
            self.text_html, self.conference, subject, body
        )

    def render_plain(self, subject, body):
        text_plain = self.text_plain
        if not text_plain:
            text_plain = html2text(self.text_html)
        return EmailFrame.render(
            text_plain, self.conference, subject, body
        )


class EmailSettings(models.Model):
    frame = models.ForeignKey(EmailFrame, on_delete=models.SET_NULL, null=True)
    conference = models.OneToOneField(
        Conference, null=True, blank=True, on_delete=models.CASCADE,
        related_name='email_settings',
    )


class EmailTemplate(models.Model):
    TYPE_USER = 'user'
    TYPE_SUBMISSION = 'submission'

    MSG_TYPE_CHOICES = (
        (None, _('Select message type')),
        (TYPE_USER, _('Message for user')),
        (TYPE_SUBMISSION, _('Message for submission authors')),
    )

    subject = models.CharField(max_length=1024)
    body = models.TextField()
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name='email_templates',
    )
    msg_type = models.CharField(
        max_length=128,
        choices=MSG_TYPE_CHOICES,
        blank=True,
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='email_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)


class GroupEmailMessage(models.Model):
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_emails'
    )
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name='sent_group_emails',
    )
    users_to = models.ManyToManyField(User, related_name='group_emails')
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='sent_group_emails'
    )
    sent = models.BooleanField(default=False)

    @staticmethod
    def create(template, users_to):
        message = GroupEmailMessage.objects.create(
            template=template,
            conference=template.conference,
        )
        for user in users_to:
            message.users_to.add(user)
        message.save()
        return message

    def send(self, sender, context=None, user_context=None):
        """Create a bunch of messages for each user and send them.

        :param sender: user that initiates message sending
        :param context: context for template rendering.
        :param user_context: `dict` with `User -> dict` items. Specific context
            for each user, e.g. link to his login page or name.
        :return: self
        """

        # 1) Update status and save sender chair user:
        self.sent = False
        self.sent_by = sender
        self.save()

        # 2) For each user, we render this template with the given context,
        #    and then build the whole message by inserting this body into
        #    the frame. Plain-text version is also formed from HTML.
        frame = self.conference.email_settings.frame
        body_template = Template(self.template.body)
        subject_template = Template(self.template.subject)
        for user in self.users_to.all():
            # Building context:
            ctx = dict(context) if context is not None else {}
            if user_context and user in user_context:
                ctx.update(user_context[user])
            _ctx = Context(ctx, autoescape=False)
            # Rendering body and subject:
            body_html = body_template.render(_ctx)
            body_plain = html2text(body_html)
            subject = subject_template.render(_ctx)
            # Rendering full email with frame and building mail instance:
            text_html = frame.render_html(subject, body_html)
            text_plain = frame.render_plain(subject, body_plain)
            message = EmailMessage.objects.create(
                user_to=user,
                group_message=self,
                subject=subject,
                text_html=text_html,
                text_plain=text_plain,
            )
            message.send(sender)

        # 3) Update self status, write sending timestamp
        self.sent_at = timezone.now()
        self.sent = True
        self.save()
        return self


class EmailMessage(models.Model):
    subject = models.TextField(max_length=1024)
    text_plain = models.TextField()
    text_html = models.TextField()
    user_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='emails'
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, null=True,
        related_name='sent_emails'
    )

    group_message = models.ForeignKey(
        GroupEmailMessage,
        on_delete=models.SET_NULL,
        null=True,
        related_name='messages',
    )

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
