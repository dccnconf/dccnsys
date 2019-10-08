from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.forms import ModelForm, HiddenInput

from gears.widgets import CustomFileInput
from .models import Conference, SubmissionStage, ReviewStage, ProceedingType, \
    SubmissionType, Topic, ProceedingVolume, ArtifactDescriptor, ExternalFile


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


class ProceedingVolumeForm(ModelForm):
    class Meta:
        model = ProceedingVolume
        fields = ['name', 'description']


class ArtifactDescriptorForm(ModelForm):
    class Meta:
        model = ArtifactDescriptor
        exclude = ['proc_type']


class ExternalFileForm(ModelForm):
    class Meta:
        model = ExternalFile
        fields = ['url', 'label']


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


class TopicCreateForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['name']

    def __init__(self, conference, *args, **kwargs):
        self.conference = conference
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        topic = super().save(commit=False)
        existing_topics = self.conference.topic_set.all()
        max_order = existing_topics.aggregate(Max('order'))['order__max']
        topic.order = 1 if max_order is None else max_order + 1
        topic.conference = self.conference
        if commit:
            super().save(commit=True)
        return topic


class TopicEditForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['name']


class TopicsReorderForm(forms.Form):
    topic_pks = forms.CharField(max_length=100, widget=forms.HiddenInput())

    def __init__(self, conference, separator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conference = conference
        self.separator = separator
        self.cleaned_keys = []

    def clean_topic_pks(self):
        pks = list(map(
            lambda s: int(s),
            self.cleaned_data['topic_pks'].split(self.separator)
        ))

        # 1) First we check that there are no duplicates in topic_pks field:
        if len(pks) != len(set(pks)):
            raise ValidationError(f'duplicate keys found in {pks}')

        # 2) Then we validate that the number of topics in the field match
        # the number of topics registered for the conference:
        num_topics_expected = self.conference.topic_set.count()
        num_topics_found = len(set(pks))
        if num_topics_expected != num_topics_found:
            raise ValidationError(
                f'expected {num_topics_expected} Topic keys, {num_topics_found} '
                f'found in {pks}')

        # 3) Finally validate all topics are found in conference topic_set:
        for pk in pks:
            if self.conference.topic_set.filter(pk=pk).count() != 1:
                raise ValidationError(
                    f'Topic with pk={pk} not found in conference topic_set')

        # If everything is ok, write the topic ids
        self.cleaned_keys = pks

    def save(self):
        for index, pk in enumerate(self.cleaned_keys):
            topic = self.conference.topic_set.get(pk=pk)
            topic.order = index + 1
            topic.save()
