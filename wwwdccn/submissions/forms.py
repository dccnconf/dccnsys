from django import forms
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from gears.widgets import CustomFileInput
from .models import Submission, Author


class CreateSubmissionForm(forms.ModelForm):
    is_author = forms.BooleanField(
        required=True,
        label=_('I confirm that I am an author of the submission')
    )

    agree_with_terms = forms.BooleanField(
        required=True,
        label=_('I agree with terms and conditions of my paper processing')
    )


    class Meta:
        model = Submission
        fields = ['conference']


class SubmissionDetailsForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['title', 'abstract', 'topics']


class UploadReviewManuscriptForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['review_manuscript']
        widgets = {
            'review_manuscript': CustomFileInput(attrs={
                'accept': '.pdf',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary',
            })
        }


# TODO: refactor this - unify this form with TopicReorderForm
# (maybe reasonable to remove validation all authors are registered within
# a given submission, remove submission from constructor, etc.)
class AuthorsReorderForm(forms.Form):
    pks = forms.CharField(max_length=100, widget=forms.HiddenInput)

    def __init__(self, submission, separator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submission = submission
        self.separator = separator
        self.cleaned_keys = []

    def clean_pks(self):
        pks = list(map(
            lambda s: int(s),
            self.cleaned_data['pks'].split(self.separator)
        ))

        # 1) First we check that there are no duplicates in pks field:
        if len(pks) != len(set(pks)):
            raise ValidationError(f'duplicate keys found in {pks}')

        # 2) Then we validate that the number of records in the field match
        # the number of records registered for the owner:
        num_expected = self.submission.authors.count()
        num_found = len(set(pks))
        if num_expected != num_found:
            raise ValidationError(
                f'expected {num_expected} keys, {num_found} found in {pks}')

        # 3) Finally validate all records are found in owner set:
        for pk in pks:
            if self.submission.authors.filter(pk=pk).count() != 1:
                raise ValidationError(
                    f'Author with pk={pk} not found in submission authors')

        # If everything is ok, write the ids:
        self.cleaned_keys = pks

    def save(self):
        for index, pk in enumerate(self.cleaned_keys):
            author = Author.objects.get(pk=pk)
            author.order = index + 1
            author.save()
