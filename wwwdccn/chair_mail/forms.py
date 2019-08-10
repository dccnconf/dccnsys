from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.utils import timezone
from html2text import html2text
from markdown import markdown

from chair_mail.context import get_conference_context, get_user_context, \
    get_submission_context
from submissions.models import Submission
from users.models import User
from .models import EmailTemplate, EmailFrame, GroupEmailMessage


class EmailFrameUpdateForm(forms.ModelForm):
    class Meta:
        model = EmailFrame
        fields = ('text_html', 'text_plain')

    def save(self, commit=True):
        template = super().save(commit=False)
        template.updated_at = timezone.now()
        if commit:
            template.save()
        return template


class EmailFrameTestForm(forms.Form):
    text_html = forms.CharField(widget=forms.Textarea())
    text_plain = forms.CharField(widget=forms.Textarea())

    def send_message(self, user, conference):
        body_html = f"<p>Dear {user.profile.get_full_name()},</p>" \
            f"<p>this is a test generated by the registration system.</p>"
        body_plain = html2text(body_html)
        subject = 'Template test'

        html = EmailFrame.render(
            self.cleaned_data['text_html'], conference, subject, body_html
        )
        plain = EmailFrame.render(
            self.cleaned_data['text_plain'], conference, subject, body_plain
        )

        send_mail(
            subject=f'[{conference.short_name}] {subject}',
            message=plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html,
        )


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ('subject', 'body')

    def save(self, commit=True, conference=None, sender=None, msg_type=None):
        template = super().save(False)
        if commit:
            template.conference = conference
            template.created_by = sender
            template.msg_type = msg_type
            template.save()
        return template


class PreviewFormBase(forms.Form):
    subject = forms.CharField(required=False)
    body = forms.CharField(widget=forms.Textarea(), required=False)

    def get_context(self, conference):
        raise NotImplementedError

    def render_html(self, conference):
        ctx_data = self.get_context(conference)
        context = Context(ctx_data, autoescape=False)
        body_template = Template(markdown(self.cleaned_data['body']))
        subject_template = Template(self.cleaned_data['subject'])
        return {
            'body': body_template.render(context),
            'subject': subject_template.render(context)
        }


class PreviewUserMessageForm(PreviewFormBase):
    user = forms.ChoiceField()

    def __init__(self, *args, users=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].choices = [
            (u.pk, u.profile.get_full_name()) for u in users
        ]
        if len(users) == 1:
            self.fields['user'].widget.attrs['hidden'] = True

    def get_context(self, conference):
        user = User.objects.get(pk=self.cleaned_data['user'])
        return {
            **get_conference_context(conference),
            **get_user_context(user, conference),
        }


class PreviewSubmissionMessageForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(), required=False)
    user = forms.ChoiceField()

    def __init__(self, *args, users=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].choices = [
            (u.pk, u.profile.get_full_name()) for u in users
        ]
