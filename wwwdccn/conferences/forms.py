from django import forms

from gears.widgets import CustomFileInput
from .models import Conference, SubmissionStage, ReviewStage, ProceedingType


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


class ProceedingTypeForm(forms.ModelForm):
    class Meta:
        model = ProceedingType
        exclude = ['conference']
        widgets = {
            'description': forms.Textarea(),
            'final_latex_template': CustomFileInput(attrs={
                'accept': '.zip',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary',
            })
        }


class ProceedingsDeleteForm(forms.Form):
    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def save(self):
        self.target.delete()
