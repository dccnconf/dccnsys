from django import forms

from conferences.helpers import get_countries_of, get_affiliations_of
from conferences.models import Conference
from gears.widgets import CustomCheckboxSelectMultiple
from submissions.models import Submission


class FilterSubmissionsForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = []

    term = forms.CharField(required=False)

    types = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    topics = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    status = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=Submission.STATUS
    )

    countries = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    affiliations = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.instance
        self.fields['types'].choices = [
            (st.pk, st) for st in self.instance.submissiontype_set.all()
        ]
        self.fields['topics'].choices = [
            (topic.pk, topic) for topic in self.instance.topic_set.all()
        ]
        all_submissions = self.instance.submission_set.all()
        self.fields['countries'].choices = [
            (cnt.code, cnt.name) for cnt in get_countries_of(all_submissions)
        ]
        self.fields['affiliations'].choices = [
            (aff, aff) for aff in get_affiliations_of(all_submissions)
        ]


class FilterUsersForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = []

    term = forms.CharField(required=False)

    attending = forms.BooleanField(required=False)

    countries = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    affiliations = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.instance
        all_submissions = self.instance.submission_set.all()
        self.fields['countries'].choices = [
            (cnt.code, cnt.name) for cnt in get_countries_of(all_submissions)
        ]
        self.fields['affiliations'].choices = [
            (aff, aff) for aff in get_affiliations_of(all_submissions)
        ]
