from django import forms

from gears.widgets import CustomFileInput
from .models import Conference, SubmissionStage, ReviewStage, ProceedingType, \
    SubmissionType


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
        exclude = ['conference', '_final_latex_template_version']
        widgets = {
            'description': forms.Textarea(),
            'final_latex_template': CustomFileInput(attrs={
                'accept': '.zip',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary btn-sm',
            })
        }


class SubmissionTypeForm(forms.ModelForm):
    class Meta:
        model = SubmissionType
        exclude = ['conference', '_latex_template_version']
        widgets = {
            'description': forms.Textarea(),
            'latex_template': CustomFileInput(attrs={
                'accept': '.zip',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary btn-sm',
            })
        }


class DeleteForm(forms.Form):
    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def save(self):
        self.target.delete()
