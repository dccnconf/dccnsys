from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.forms import Form, MultipleChoiceField, CharField
from django.utils.translation import ugettext_lazy as _

from conferences.models import Conference
from gears.widgets import CustomCheckboxSelectMultiple, CustomFileInput
from review.models import Reviewer, Review, Decision, ReviewStats
from review.utilities import get_average_score, count_required_reviews, \
    count_missing_reviews, review_finished
from submissions.models import Submission
from users.models import Profile

User = get_user_model()

COMPLETION_STATUS = [
    ('EMPTY', 'Empty submissions'),
    ('INCOMPLETE', 'Incomplete submissions'),
    ('COMPLETE', 'Complete submissions'),
]


def search_submissions(submissions, term, sub_profiles=None):
    if sub_profiles is None:
        sub_profiles = {
            sub: Profile.objects.filter(user__authorship__submission=sub)
            for sub in submissions
        }
    if term:
        words = term.lower().split()
        return [sub for sub in submissions
                if all(word in sub.title.lower() or
                       word in str(sub.pk) or
                       any(word in pr.get_full_name().lower()
                           for pr in sub_profiles[sub]) or
                       any(word in pr.get_full_name_rus().lower()
                           for pr in sub_profiles[sub])
                       for word in words)]
    return [sub for sub in submissions]


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
        choices=Submission.STATUS_CHOICE
    )

    countries = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    affiliations = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self.instance, Conference)

        self.fields['types'].choices = [
            (st.pk, st) for st in self.instance.submissiontype_set.all()
        ]
        self.fields['topics'].choices = [
            (topic.pk, topic) for topic in self.instance.topic_set.all()
        ]

        # Getting profiles of all participants:
        profiles = Profile.objects.filter(
            user__authorship__submission__conference__pk=self.instance.pk
        ).distinct()

        # Extracting all the different countries:
        countries = list(set(p.country for p in profiles))
        countries.sort(key=lambda cnt: cnt.name)
        self.fields['countries'].choices = [
            (cnt.code, cnt.name) for cnt in countries
        ]

        # Extracting all the different affiliations:
        affs = [item['affiliation'] for item in profiles.values('affiliation')]
        affs.sort()
        self.fields['affiliations'].choices = [(item, item) for item in affs]

    def apply(self, submissions):
        term = self.cleaned_data['term']
        completion = self.cleaned_data['completion']
        types = [int(t) for t in self.cleaned_data['types']]
        topics = [int(topic) for topic in self.cleaned_data['topics']]
        status = self.cleaned_data['status']
        countries = self.cleaned_data['countries']
        affiliations = self.cleaned_data['affiliations']

        auth_prs = {
            sub: Profile.objects.filter(user__authorship__submission=sub)
            for sub in submissions
        }
        if term:
            submissions = search_submissions(
                submissions, term, sub_profiles=auth_prs)

        if completion:
            _show_incomplete = 'INCOMPLETE' in completion
            _show_complete = 'COMPLETE' in completion
            _show_empty = 'EMPTY' in completion

            _sub_warnings = {sub: sub.warnings() for sub in submissions}

            submissions = [
                sub for sub in submissions
                if (_sub_warnings[sub] and _show_incomplete or
                    not _sub_warnings[sub] and _show_complete or
                    not sub.title and _show_empty)
            ]

        if topics:
            _sub_topics = {
                sub: set(x[0] for x in sub.topics.values_list('pk'))
                for sub in submissions
            }
            submissions = [
                sub for sub in submissions
                if any(topic in _sub_topics[sub] for topic in topics)
            ]

        if types:
            submissions = [sub for sub in submissions
                           if sub.stype and sub.stype.pk in types]

        if status:
            submissions = [sub for sub in submissions if sub.status in status]

        if countries:
            submissions = [
                sub for sub in submissions
                if any(pr.country.code in countries for pr in auth_prs[sub])
            ]

        if affiliations:
            submissions = [
                sub for sub in submissions
                if any(pr.affiliation in affiliations for pr in auth_prs[sub])
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
        assert isinstance(self.instance, Conference)

        # Getting profiles of all participants:
        profiles = Profile.objects.filter(
            user__authorship__submission__conference__pk=self.instance.pk
        ).distinct()

        # Extracting all the different countries:
        countries = list(set(p.country for p in profiles))
        countries.sort(key=lambda cnt: cnt.name)
        self.fields['countries'].choices = [
            (cnt.code, cnt.name) for cnt in countries
        ]

        # Extracting all the different affiliations:
        affs = [item['affiliation'] for item in profiles.values('affiliation')]
        affs.sort()
        self.fields['affiliations'].choices = [(item, item) for item in affs]

    def apply(self, users):
        term = self.cleaned_data['term']
        attending_status = self.cleaned_data['attending_status']
        countries = self.cleaned_data['countries']
        affiliations = self.cleaned_data['affiliations']

        #
        # Here we map users list to profiles, then work with profiles and
        # finally map filtered profiles back to users.
        #
        # This is done for performance reasons to avoid huge number of
        # duplicated SQL queries when requesting foreign key object via
        # `user.profile` call.
        #
        # This optimization allowed to increase the filter speed more than
        # 10 times.
        #
        profiles = list(Profile.objects.filter(user__in=users))

        if term:
            words = term.lower().split()
            profiles = [
                profile for profile in profiles
                if all(any(word in string for string in [
                    profile.get_full_name().lower(),
                    profile.get_full_name_rus().lower(),
                    profile.affiliation.lower(),
                    profile.get_country_display().lower()
                ]) for word in words)
            ]

        if attending_status:
            _show_attending = 'YES' in attending_status
            _show_not_attending = 'NO' in attending_status

            attending_profiles = Profile.objects.filter(
                user__authorship__submission__conference=self.instance
            ).distinct()

            profiles = [
                profile for profile in profiles
                if (profile in attending_profiles and _show_attending or
                    profile not in attending_profiles and _show_not_attending)
            ]

        if countries:
            profiles = [
                profile for profile in profiles
                if profile.country.code in countries
            ]

        if affiliations:
            profiles = [
                profile for profile in profiles
                if profile.affiliation in affiliations
            ]

        users = User.objects.filter(profile__in=profiles)

        return users


class ChairUploadReviewManuscriptForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('review_manuscript',)
        widgets = {
            'review_manuscript': CustomFileInput(attrs={
                'accept': '.pdf',
                'show_file_name': True,
                'btn_class': 'btn-outline-secondary',
                'label': _('Review manuscript PDF file')
            })
        }


class AssignReviewerForm(forms.Form):
    reviewer = forms.ChoiceField(required=True, label=_('Assign reviewer'))

    def __init__(self, *args, submission=None):
        super().__init__(*args)
        self.submission = submission

        # Fill available reviewers - neither already assigned, nor authors:
        reviews = submission.reviews.all()
        assigned_reviewers = reviews.values_list('reviewer', flat=True)
        authors_users = submission.authors.values_list('user', flat=True)
        available_reviewers = Reviewer.objects.exclude(
            Q(pk__in=assigned_reviewers) | Q(user__in=authors_users)
        )
        profiles = {
            rev: rev.user.profile for rev in available_reviewers
        }
        reviewers = list(available_reviewers)
        reviewers.sort(key=lambda r: r.reviews.count())
        self.fields['reviewer'].choices = (
            (rev.pk,
             f'{profiles[rev].get_full_name()} ({rev.reviews.count()}) - '
             f'{profiles[rev].affiliation}, '
             f'{profiles[rev].get_country_display()}')
            for rev in reviewers
        )

    def save(self):
        reviewer = Reviewer.objects.get(pk=self.cleaned_data['reviewer'])
        review = Review.objects.create(reviewer=reviewer, paper=self.submission)
        return review


class FilterReviewsForm(Form):
    Q1 = 'Q1'
    Q2 = 'Q2'
    Q3 = 'Q3'
    Q4 = 'Q4'
    QUARTILES_CHOICES = (
        (Q1, _('Q1 (lowest 25%)')), (Q2, 'Q2'), (Q3, 'Q3'),
        (Q4, _('Q4 (top 25%)')))

    REVIEW_COMPLETED = 'COMPLETED'
    REVIEW_ASSIGNED_INCOMPLETE = 'ASSIGNED_INCOMPLETE'
    REVIEW_NOT_ASSIGNED = 'NOT_ASSIGNED'
    COMPLETION_CHOICES = (
        (REVIEW_COMPLETED, _('All reviews assigned and completed')),
        (REVIEW_ASSIGNED_INCOMPLETE,
         _('All reviews assigned, but some not finished')),
        (REVIEW_NOT_ASSIGNED,
         _('One or more reviewer not assigned')))

    term = CharField(required=False)

    quartiles = MultipleChoiceField(
        choices=QUARTILES_CHOICES, widget=CustomCheckboxSelectMultiple,
        required=False)

    decisions = MultipleChoiceField(
        choices=Decision.DECISION_CHOICES, widget=CustomCheckboxSelectMultiple,
        required=False)

    completion = MultipleChoiceField(
        choices=COMPLETION_CHOICES, widget=CustomCheckboxSelectMultiple,
        required=False)

    status = MultipleChoiceField(
        choices=Submission.STATUS_CHOICE, widget=CustomCheckboxSelectMultiple,
        required=False)

    def __init__(self, *args, instance=None, **kwargs):
        if not isinstance(instance, Conference):
            raise TypeError(
                f'expected Conference instance, {type(instance)} found')
        super().__init__(*args, **kwargs)
        self.instance = instance

    def apply_quartiles(self, submissions):
        quartiles = self.cleaned_data['quartiles']
        if quartiles:
            stats, _ = ReviewStats.objects.get_or_create(
                conference=self.instance)
            scores = {sub: get_average_score(sub) for sub in submissions}
            if self.Q1 not in quartiles:
                submissions = [
                    sub for sub in submissions if scores[sub] >= stats.q1_score]
            if self.Q2 not in quartiles:
                submissions = [sub for sub in submissions
                               if scores[sub] < stats.q1_score
                               or scores[sub] >= stats.median_score]
            if self.Q3 not in quartiles:
                submissions = [sub for sub in submissions
                               if scores[sub] < stats.median_score
                               or scores[sub] >= stats.q3_score]
            if self.Q4 not in quartiles:
                submissions = [sub for sub in submissions
                               if scores[sub] < stats.q3_score]
        return submissions

    def apply_decisions(self, submissions):
        selected = self.cleaned_data['decisions']
        if selected:
            decisions = {sub: sub.review_decision for sub in submissions}
            allow_undefined = Decision.UNDEFINED in selected
            submissions = [sub for sub in submissions
                           if ((not decisions[sub] and allow_undefined) or
                               (decisions[sub].first().decision in selected))]
        return submissions

    def apply_completion(self, submissions):
        selected = self.cleaned_data['completion']
        cached_stypes = {
            st.pk: st for st in self.instance.submissiontype_set.all()}

        def get_completion(submission):
            if review_finished(submission, cached_stypes=cached_stypes):
                return self.REVIEW_COMPLETED
            nr = count_required_reviews(submission, cached_stypes=cached_stypes)
            if submission.reviews.count() < nr:
                return self.REVIEW_NOT_ASSIGNED
            return self.REVIEW_ASSIGNED_INCOMPLETE

        if selected:
            submissions = [sub for sub in submissions
                           if get_completion(sub) in selected]
        return submissions

    def apply_status(self, submissions):
        selected = self.cleaned_data['status']
        if selected:
            submissions = [sub for sub in submissions
                           if sub.status in selected]
        return submissions

    def apply(self, submissions):
        submissions = search_submissions(submissions, self.cleaned_data['term'])
        submissions = self.apply_quartiles(submissions)
        submissions = self.apply_decisions(submissions)
        submissions = self.apply_completion(submissions)
        submissions = self.apply_status(submissions)
        return submissions
