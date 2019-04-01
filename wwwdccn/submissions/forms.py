from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from gears.widgets import CustomFileInput
from .models import Submission, Author

User = get_user_model()


MIN_TOPICS_REQUIRED = 1
MAX_TOPICS_REQUIRED = 3


class CreateSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['conference']

    is_author = forms.BooleanField(
        required=True,
        label=_('I confirm that I am an author of the submission')
    )

    agree_with_terms = forms.BooleanField(
        required=True,
        label=_('I agree with terms and conditions of my paper processing')
    )


class SubmissionDetailsForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['title', 'abstract', 'topics', 'stype']
        widgets = {
            'abstract': forms.Textarea(attrs={'rows': 4}),
            'topics': forms.CheckboxSelectMultiple(attrs={
                'required': False,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['topics'].required = False

    def clean_topics(self):
        print('Hello!')
        num_topics = len(self.cleaned_data['topics'])
        print(num_topics)
        if num_topics < MIN_TOPICS_REQUIRED:
            raise ValidationError(
                _('At least %(min_topics)s topic must be selected'),
                params={'min_topics': MIN_TOPICS_REQUIRED},
                code='invalid_topics',
            )
        elif num_topics > MAX_TOPICS_REQUIRED:
            raise ValidationError(
                _('At most %(max_topics)s topics can be selected'),
                params={'max_topics': MAX_TOPICS_REQUIRED},
                code='invalid_topics',
            )
        return self.cleaned_data['topics']



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

    def save(self, commit=True):
        for index, pk in enumerate(self.cleaned_keys):
            author = Author.objects.get(pk=pk)
            author.order = index + 1
            if commit:
                author.save()
        for author in self.submission.authors.all():
            print(author)


class AuthorCreateForm(forms.Form):
    user_pk = forms.IntegerField()

    def __init__(self, submission, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submission = submission
        self.user = None

    def clean_user_pk(self):
        user_pk = self.cleaned_data['user_pk']
        self.user = User.objects.get(pk=user_pk)
        for author in self.submission.authors.all():
            if author.user.pk == self.user.pk:
                raise ValidationError(f'Author already added')
        return self.cleaned_data['user_pk']

    # def clean(self):
    #     super().clean()
    #     print(self.clean_user_pk())
    #     print('cleaned data: ', self.cleaned_data)
    #     return self.cleaned_data
    #
    def save(self, commit=True):
        authors = self.submission.authors
        max_order = authors.aggregate(Max('order'))['order__max']
        author = Author.objects.create(
            user=self.user,
            submission=self.submission,
            order=1 if max_order is None else max_order + 1
        )
        if commit:
            author.save()
        return author


class AuthorDeleteForm(forms.Form):
    author_pk = forms.IntegerField()

    def __init__(self, submission, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submission = submission
        self.author = None

    def clean_author_pk(self):
        # Check that we are not deleting the creator
        author_pk = self.cleaned_data['author_pk']
        self.author = Author.objects.get(pk=author_pk)
        creator = self.submission.created_by
        if self.author.user.pk == creator.pk:
            raise ValidationError(_('Can not delete submission creator'))
        if self.author.submission.pk != self.submission.pk:
            raise ValidationError(_('Can not delete alien author'))
        return self.cleaned_data['author_pk']

    def save(self, commit=True):
        print(self.author)
        if commit:
            self.author.delete()
