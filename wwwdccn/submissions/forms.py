from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Max
from django.forms import ModelForm
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from gears.widgets import CustomFileInput
from .models import Submission, Author, Attachment

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

    def clean_conference(self):
        conference = self.cleaned_data['conference']
        if conference.submission_stage.end_date < timezone.now():
            raise ValidationError(
                _('Submission impossible since deadline passed')
            )
        return self.cleaned_data['conference']

    def save(self, commit=True):
        return super().save(False)


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
        num_topics = len(self.cleaned_data['topics'])
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

    def save(self, commit=True):
        submission = super().save(commit=commit)
        if commit and not submission.filled_details:
            submission.filled_details = True
            submission.save()
        return submission


class UploadReviewManuscriptForm(forms.ModelForm):
    confirm_blind = forms.BooleanField(
        required=False,
        label=_('I confirm that the uploaded PDF is prepared for blind review. '
                'It does not contain any information that can be used to '
                'identify its authors. In particular, no authors names or '
                'references to funding sources is given.')
    )

    understand_blind_review = forms.BooleanField(
        required=False,
        label=_('I understand that the paper may be rejected during the review '
                'if it names the authors in some way.')
    )

    class Meta:
        model = Submission
        fields = ['review_manuscript']
        widgets = {
            'review_manuscript': CustomFileInput(attrs={
                'accept': '.pdf',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary',
                'label': _('Review manuscript PDF file')
            })
        }

    def has_manuscript(self):
        return (bool(self.cleaned_data['review_manuscript']) or
                bool(self.instance and self.instance.review_manuscript))

    def clean(self):
        confirmed_blind = self.cleaned_data.get('confirm_blind')
        understand = self.cleaned_data.get('understand_blind_review')
        if self.has_manuscript() and not (confirmed_blind and understand):
            if not confirmed_blind:
                self.add_error('confirm_blind', '')
            if not understand:
                self.add_error('understand_blind_review', '')
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None and self.instance.review_manuscript:
            self.fields['confirm_blind'].initial = 'True'
            self.fields['understand_blind_review'].initial = True


# TODO: refactor this - unify this form with TopicReorderForm
# (maybe reasonable to remove validation all authors are registered within
# a given submission, remove submission from constructor, etc.)
class AuthorsReorderForm(forms.Form):
    pks = forms.CharField(max_length=100, widget=forms.HiddenInput)

    def __init__(self, submission, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submission = submission
        self.separator = kwargs.get('separator', ',')
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
        if commit:
            self.author.delete()


class InviteAuthorForm(forms.Form):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    def save(self, request, submission):
        context = {
            'email': self.cleaned_data['email'],
            'sender': request.user,
            'first_name': self.cleaned_data['first_name'],
            'last_name': self.cleaned_data['last_name'],
            'submission': submission,
            'protocol': 'https' if request.is_secure() else "http",
            'domain': request.get_host(),
        }
        html = render_to_string('submissions/email/invitation.html', context)
        text = render_to_string('submissions/email/invitation.txt', context)
        send_mail(
            'Invitation to DCCN Conference Registration System',
            message=text,
            html_message=html,
            recipient_list=[self.cleaned_data['email']],
            from_email=settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
        )


class UploadAttachmentForm(ModelForm):
    class Meta:
        model = Attachment
        fields = ['file']

    def has_file(self):
        return (bool(self.cleaned_data['file']) or
                bool(self.instance and self.instance.file))


class UpdateSubmissionStatusForm(ModelForm):
    class Meta:
        model = Submission
        fields = ['status']
