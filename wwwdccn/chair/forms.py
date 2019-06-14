from django import forms

from conferences.helpers import get_countries_of, get_affiliations_of
from conferences.models import Conference
from gears.widgets import CustomCheckboxSelectMultiple
from submissions.models import Submission


COMPLETION_STATUS = [
    ('EMPTY', 'Empty submissions'),
    ('INCOMPLETE', 'Incomplete submissions'),
    ('COMPLETE', 'Complete submissions'),
]


class FilterSubmissionsForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = []

    term = forms.CharField(required=False)

    completion = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=COMPLETION_STATUS,
    )

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

    def apply(self, submissions):
        term = self.cleaned_data['term']
        completion = self.cleaned_data['completion']
        types = [int(t) for t in self.cleaned_data['types']]
        topics = [int(topic) for topic in self.cleaned_data['topics']]
        status = self.cleaned_data['status']
        countries = self.cleaned_data['countries']
        affiliations = self.cleaned_data['affiliations']

        if term:
            words = term.lower().split()
            submissions = [
                sub for sub in submissions
                if all(word in sub.title.lower() or
                       any(word in a.user.profile.get_full_name().lower()
                           for a in sub.authors.all()) or
                       any(word in a.user.profile.get_full_name_rus().lower()
                           for a in sub.authors.all())
                       for word in words)
            ]

        print('incomplete: ', completion)

        if completion:
            _show_incomplete = 'INCOMPLETE' in completion
            _show_complete = 'COMPLETE' in completion
            _show_empty = 'EMPTY' in completion
            submissions = [
                sub for sub in submissions
                if (sub.warnings() and _show_incomplete or
                    not sub.warnings() and _show_complete or
                    not sub.title and _show_empty)
            ]

        if topics:
            submissions = [
                sub for sub in submissions
                if any(topic in [t.pk for t in sub.topics.all()]
                       for topic in topics)
            ]

        if types:
            submissions = [sub for sub in submissions
                           if sub.stype and sub.stype.pk in types]

        if status:
            submissions = [sub for sub in submissions if sub.status in status]

        if countries:
            submissions = [
                sub for sub in submissions
                if any(author.user.profile.country.code in countries
                       for author in sub.authors.all())
            ]

        if affiliations:
            submissions = [
                sub for sub in submissions
                if any(author.user.profile.affiliation in affiliations
                       for author in sub.authors.all())
            ]

        return submissions


ATTENDING_STATUS = (
    ('YES', 'Attending'),
    ('NO', 'Not attending'),
)


class FilterUsersForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = []

    term = forms.CharField(required=False)

    attending_status = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=ATTENDING_STATUS,
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
        all_submissions = self.instance.submission_set.all()
        self.fields['countries'].choices = [
            (cnt.code, cnt.name) for cnt in get_countries_of(all_submissions)
        ]
        self.fields['affiliations'].choices = [
            (aff, aff) for aff in get_affiliations_of(all_submissions)
        ]

    def apply(self, users, conference):
        term = self.cleaned_data['term']
        attending_status = self.cleaned_data['attending_status']
        countries = self.cleaned_data['countries']
        affiliations = self.cleaned_data['affiliations']

        if term:
            words = term.lower().split()
            users = [
                user for user in users
                if all(any(word in string for string in [
                    user.profile.get_full_name().lower(),
                    user.profile.get_full_name_rus().lower(),
                    user.profile.affiliation.lower(),
                    user.profile.get_country_display().lower()
                    ]) for word in words)
            ]

        if attending_status:
            _show_attending = 'YES' in attending_status
            _show_not_attending = 'NO' in attending_status
            _user_attending_map = {
                u: any(author.submission.conference == conference
                       for author in u.authorship.all()) for u in users}

            users = [
                user for user in users
                if (_user_attending_map[user] and _show_attending or
                    not _user_attending_map[user] and _show_not_attending)
            ]

        if countries:
            users = [
                user for user in users if user.profile.country.code in countries
            ]

        if affiliations:
            users = [
                user for user in users
                if user.profile.affiliation in affiliations
            ]

        return users
