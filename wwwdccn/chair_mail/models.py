from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models import ForeignKey, OneToOneField, TextField, CharField, \
    SET_NULL, CASCADE, BooleanField, UniqueConstraint
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import Template, Context
from django.utils import timezone
from markdown import markdown
from html2text import html2text

from chair_mail.context import get_conference_context, get_user_context, \
    get_submission_context, get_frame_context
from conferences.models import Conference
from submissions.models import Submission
from users.models import User

MSG_TYPE_USER = 'user'
MSG_TYPE_SUBMISSION = 'submission'

MESSAGE_TYPE_CHOICES = (
    (MSG_TYPE_USER, 'Message to users'),
    (MSG_TYPE_SUBMISSION, 'Message to submissions'),
)


class EmailFrame(models.Model):
    text_html = models.TextField()
    text_plain = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    @staticmethod
    def render(frame_template, conference, subject, body):
        context_data = get_frame_context(conference, subject, body)
        context = Context(context_data, autoescape=False)
        return Template(frame_template).render(context)

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


class GroupMessage(models.Model):
    subject = models.CharField(max_length=1024)
    body = models.TextField()
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name='sent_group_emails',
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='sent_group_emails'
    )
    sent = models.BooleanField(default=False)

    @property
    def message_type(self):
        return ''


class UserMessage(GroupMessage):
    recipients = models.ManyToManyField(User, related_name='group_emails')

    group_message = models.OneToOneField(
        GroupMessage, on_delete=models.CASCADE, parent_link=True)

    @property
    def message_type(self):
        return MSG_TYPE_USER

    @staticmethod
    def create(subject, body, conference, objects_to):
        msg = UserMessage.objects.create(
            subject=subject, body=body, conference=conference)
        for user in objects_to:
            msg.recipients.add(user)
        msg.save()
        return msg

    def send(self, sender):
        # 1) Update status and save sender chair user:
        self.sent = False
        self.sent_by = sender
        self.save()

        # 2) For each user, we render this template with the given context,
        #    and then build the whole message by inserting this body into
        #    the frame. Plain-text version is also formed from HTML.
        frame = self.conference.email_settings.frame
        conference_context = get_conference_context(self.conference)
        for user in self.recipients.all():
            context = Context({
                **conference_context,
                **get_user_context(user, self.conference)
            }, autoescape=False)
            email = EmailMessage.create(
                group_message=self.group_message,
                user_to=user,
                context=context,
                frame=frame
            )
            email.send(sender)

        # 3) Update self status, write sending timestamp
        self.sent_at = timezone.now()
        self.sent = True
        self.save()
        return self


class SubmissionMessage(GroupMessage):
    recipients = models.ManyToManyField(
        Submission, related_name='group_emails')

    group_message = models.OneToOneField(
        GroupMessage, on_delete=models.CASCADE, parent_link=True)

    @property
    def message_type(self):
        return MSG_TYPE_SUBMISSION

    @staticmethod
    def create(subject, body, conference, objects_to):
        msg = SubmissionMessage.objects.create(
            subject=subject, body=body, conference=conference)
        for submission in objects_to:
            msg.recipients.add(submission)
        msg.save()
        return msg

    def send(self, sender):
        # 1) Update status and save sender chair user:
        self.sent = False
        self.sent_by = sender
        self.save()

        # 2) For each user, we render this template with the given context,
        #    and then build the whole message by inserting this body into
        #    the frame. Plain-text version is also formed from HTML.
        frame = self.conference.email_settings.frame
        conference_context = get_conference_context(self.conference)
        for submission in self.recipients.all():
            submission_context = get_submission_context(submission)
            for author in submission.authors.all():
                user = author.user
                context = Context({
                    **conference_context,
                    **submission_context,
                    **get_user_context(user, self.conference)
                }, autoescape=False)
                email = EmailMessage.create(
                    group_message=self.group_message,
                    user_to=user,
                    context=context,
                    frame=frame
                )
                email.send(sender)

        # 3) Update self status, write sending timestamp
        self.sent_at = timezone.now()
        self.sent = True
        self.save()
        return self


def get_group_message_model(msg_type):
    return {
        MSG_TYPE_USER: UserMessage,
        MSG_TYPE_SUBMISSION: SubmissionMessage,
    }[msg_type]


def get_message_leaf_model(msg):
    """If provided a `GroupMessage` instance, check the inheritance, find
    the most descent child and return it. Now the possible leaf models are
    `UserMessage` and `SubmissionMessage`."""
    if hasattr(msg, 'usermessage'):
        return msg.usermessage
    elif hasattr(msg, 'submissionmessage'):
        return msg.submissionmessage
    # Also check, maybe a message is already a leaf:
    if isinstance(msg, UserMessage) or isinstance(msg, SubmissionMessage):
        return msg
    # If neither succeeded, raise an error:
    raise TypeError(f'Not a group message: type(msg)')


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
        GroupMessage,
        on_delete=models.SET_NULL,
        null=True,
        related_name='messages',
    )

    @staticmethod
    def create(group_message, user_to, context, frame):
        template_body = Template(group_message.body)
        template_subject = Template(group_message.subject)
        body_md = template_body.render(context)
        body_html = markdown(body_md)
        subject = template_subject.render(context)
        return EmailMessage.objects.create(
            user_to=user_to,
            group_message=group_message,
            subject=subject,
            text_html=frame.render_html(subject, body_html),
            text_plain=frame.render_plain(subject, body_md),
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


class SystemNotification(models.Model):
    """This model represents a system notification fired on a specific event.

    The model itself doesn't define the circumstances in which the message
    must be sent, which are subject to views.

    Notification is defined with a mandatory name, optional description,
    subject and template. If template is not assigned or subject is not
    specified, messages won't be sent.

    Notification can also be turned off with `is_active` flag field.
    """
    ASSIGN_STATUS_SUBMIT = 'assign_status_submit'
    ASSIGN_STATUS_REVIEW = 'assign_status_review'

    NAME_CHOICES = (
        (ASSIGN_STATUS_REVIEW, 'Assign status review to the paper'),
        (ASSIGN_STATUS_SUBMIT, 'Assign status submit to the paper'),
    )

    name = CharField(max_length=64, choices=NAME_CHOICES)
    subject = CharField(max_length=1024, blank=True)
    is_active = BooleanField(default=False)
    type = CharField(max_length=64, choices=MESSAGE_TYPE_CHOICES, blank=False)
    body = TextField(blank=True)
    conference = ForeignKey(Conference, related_name='notifications',
                            on_delete=CASCADE)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['conference', 'name'], name='unique_name'),
        ]

    def send(self, recipients, sender=None):
        if self.is_active and self.body and self.subject:
            message_class = get_group_message_model(self.type)
            message = message_class.create(
                self.subject, self.body, self.conference, recipients)
            message.send(sender)


DEFAULT_NOTIFICATIONS_DATA = {
    SystemNotification.ASSIGN_STATUS_REVIEW: {
        'subject': 'Submission #{{ paper_id }} is under review',
        'type': MSG_TYPE_SUBMISSION,
        'body': '''Dear {{ username }},

your submission #{{ paper_id }} **"{{ paper_title }}"** is assigned for the review.

Reviews are expected to be ready at **{{ rev_end_date|time:"H:i:s" }}**.'''
    },
    SystemNotification.ASSIGN_STATUS_SUBMIT: {
        'subject': 'Submission #{{ paper_id }} is in draft editing state',
        'type': MSG_TYPE_SUBMISSION,
        'body': '''Dear {{ username }},

your submission #{{ paper_id }} **"{{ paper_title }}"** is in draft editing 
state. 

At this point you can modify review manuscript, title and other data if you 
need.'''
    },
}
