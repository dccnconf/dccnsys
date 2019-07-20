from django import forms
from django.utils import timezone

from .models import EmailTemplate


class EmailTemplateUpdateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ('text_html', 'text_plain')

    def save(self, commit=True):
        template = super().save(commit=False)
        template.updated_at = timezone.now()
        if commit:
            template.save()
        return template
