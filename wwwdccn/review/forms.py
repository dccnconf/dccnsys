from django import forms
from django.forms import Form, HiddenInput, CharField, ChoiceField, ModelForm

from conferences.models import ProceedingType, ProceedingVolume
from review.models import Review, check_review_details, ReviewDecision


class EditReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = [
            'technical_merit', 'relevance', 'originality', 'clarity',
            'details', 'submitted'
        ]

    submitted = forms.BooleanField(required=False)
    technical_merit = forms.ChoiceField(choices=Review.SCORE_CHOICES, required=False)
    relevance = forms.ChoiceField(choices=Review.SCORE_CHOICES, required=False)
    originality = forms.ChoiceField(choices=Review.SCORE_CHOICES, required=False)
    details = forms.CharField(widget=forms.Textarea(attrs={'rows': '5'}), required=False)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['submitted']:
            # If the review is submitted, it must provide scores and details
            # with the number of words as specified in the submission type:
            is_incomplete = False
            for score_field in self.instance.score_fields().keys():
                if not cleaned_data[score_field]:
                    self.add_error(score_field, 'Must select a score')
                    is_incomplete = True
            stype = self.instance.paper.stype
            if not check_review_details(cleaned_data['details'], stype):
                self.add_error(
                    'details',
                    f'Review details must have at least '
                    f'{stype.min_num_words_in_review} words'
                )
                is_incomplete = True
            if is_incomplete:
                self.cleaned_data['submitted'] = False
                raise forms.ValidationError('Review is incomplete')
        return cleaned_data


class UpdateReviewDecisionForm(ModelForm):
    class Meta:
        model = ReviewDecision
        fields = ['decision_type']


class UpdateVolumeForm(Form):
    volume = CharField(widget=HiddenInput(), required=False)

    def __init__(self, *args, instance=None, **kwargs):
        if not instance:
            raise ValueError('Decision instance is required')
        self.instance = instance
        kwargs.update({
            'initial': {
                'volume': str(instance.volume.pk) if instance.volume else '',
            }
        })
        super().__init__(*args, **kwargs)
        self.volume = None

    def clean_volume(self):
        try:
            pk = int(self.cleaned_data['volume'])
            volumes = ProceedingVolume.objects.filter(pk=pk)
            self.volume = volumes.first() if volumes.count() else None
        except ValueError:
            self.volume = None
        return self.cleaned_data['volume']

    def save(self, commit=True):
        self.instance.volume = self.volume
        if commit:
            self.instance.save()
        return self.instance
