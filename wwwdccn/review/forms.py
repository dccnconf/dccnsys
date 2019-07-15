from django import forms

from review.models import Review, check_review_details


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
