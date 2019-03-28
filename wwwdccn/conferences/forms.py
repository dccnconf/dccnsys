from django import forms

from gears.widgets import CustomFileInput
from .models import Conference, SubmissionStage, ReviewStage


class ConferenceForm(forms.ModelForm):
    class Meta:
        model = Conference
        exclude = ['creator']
        widgets = {
            'logotype': CustomFileInput(attrs={
                'accept': 'image/*',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary',
            })
        }


class SubmissionStageForm(forms.ModelForm):
    class Meta:
        model = SubmissionStage
        exclude = ['conference']


class ReviewStageForm(forms.ModelForm):
    class Meta:
        model = ReviewStage
        exclude = ['conference']
