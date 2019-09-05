from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.forms import Form, MultipleChoiceField, CharField
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from conferences.models import Conference, ProceedingVolume
from gears.widgets import CustomCheckboxSelectMultiple, CustomFileInput
from review.models import Reviewer, Review, Decision, ReviewStats
from review.utilities import get_average_score, count_required_reviews, \
    review_finished
from submissions.models import Submission
from users.models import Profile

User = get_user_model()

COMPLETION_STATUS = [
    ('EMPTY', 'Empty submissions'),
    ('INCOMPLETE', 'Incomplete submissions'),
    ('COMPLETE', 'Complete submissions'),
]


def clean_data_to_int(iterable, empty=None):
    return [int(x) if x != '' else None for x in iterable]


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

    proc_types = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    sub_types = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False
    )

    volumes = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False
    )

    def __init__(self, *args, instance=None, **kwargs):
        if not isinstance(instance, Conference):
            raise TypeError(
                f'expected Conference instance, {type(instance)} found')
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields['proc_types'].choices = [('', 'Undefined')] + [
            (pt.pk, pt.name) for pt in self.instance.proceedingtype_set.all()
        ]
        self.fields['sub_types'].choices = [('', 'Undefined')] + [
            (st.pk, st.name) for st in self.instance.submissiontype_set.all()
        ]
        self.fields['volumes'].choices = [('', 'Undefined')] + [
            (vol.pk, vol.name) for vol in
            ProceedingVolume.objects.filter(type__conference=self.instance)]

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
            decisions = {
                sub: getattr(sub.review_decision.first(), 'decision', None)
                for sub in submissions
            }
            allow_undefined = Decision.UNDEFINED in selected
            submissions = [sub for sub in submissions
                           if ((not decisions[sub] and allow_undefined) or
                               (decisions[sub] in selected))]
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

    def apply_proc_types(self, submissions):
        selected = clean_data_to_int(self.cleaned_data['proc_types'])
        if selected:
            proc_types = {
                sub: getattr(sub.review_decision.first(), 'proc_type_id', None)
                for sub in submissions
            }
            submissions = [sub for sub in submissions
                           if proc_types[sub] in selected]
        return submissions

    def apply_sub_types(self, submissions):
        selected = clean_data_to_int(self.cleaned_data['sub_types'])
        if selected:
            submissions = [sub for sub in submissions
                           if sub.stype_id in selected]
        return submissions

    def apply_volumes(self, submissions):
        selected = clean_data_to_int(self.cleaned_data['volumes'])
        if selected:
            volumes = {
                sub: getattr(sub.review_decision.first(), 'volume_id', None)
                for sub in submissions
            }
            submissions = [sub for sub in submissions
                           if volumes[sub] in selected]
        return submissions

    def apply(self, submissions):
        submissions = search_submissions(submissions, self.cleaned_data['term'])
        submissions = self.apply_quartiles(submissions)
        submissions = self.apply_decisions(submissions)
        submissions = self.apply_completion(submissions)
        submissions = self.apply_status(submissions)
        submissions = self.apply_proc_types(submissions)
        submissions = self.apply_sub_types(submissions)
        submissions = self.apply_volumes(submissions)
        return submissions


class ExportSubmissionsForm(Form):
    ORDER_COLUMN = '#'
    ID_COLUMN = 'ID'
    AUTHORS_COLUMN = 'AUTHORS'
    TITLE_COLUMN = 'TITLE'
    COUNTRY_COLUMN = 'COUNTRY'
    STYPE_COLUMN = 'TYPE'
    REVIEW_PAPER_COLUMN = 'REVIEW_MANUSCRIPT'
    REVIEW_SCORE_COLUMN = 'REVIEW_SCORE'
    STATUS_COLUMN = 'STATUS'
    TOPICS_COLUMN = 'TOPICS'
    PTYPE_COLUMN = 'PROCEEDINGS'
    VOLUME_COLUMN = 'VOLUME'

    # noinspection DuplicatedCode
    COLUMNS = (
        (ORDER_COLUMN, ORDER_COLUMN),
        (ID_COLUMN, ID_COLUMN),
        (TITLE_COLUMN, TITLE_COLUMN),
        (AUTHORS_COLUMN, AUTHORS_COLUMN),
        (COUNTRY_COLUMN, COUNTRY_COLUMN),
        (STYPE_COLUMN, STYPE_COLUMN),
        (REVIEW_PAPER_COLUMN, REVIEW_PAPER_COLUMN),
        (REVIEW_SCORE_COLUMN, REVIEW_SCORE_COLUMN),
        (STATUS_COLUMN, STATUS_COLUMN),
        (TOPICS_COLUMN, TOPICS_COLUMN),
        (PTYPE_COLUMN, PTYPE_COLUMN),
        (VOLUME_COLUMN, VOLUME_COLUMN),
    )

    status = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=Submission.STATUS_CHOICE)

    columns = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False, choices=COLUMNS)

    def __init__(self, *args, conference=None, **kwargs):
        super().__init__(*args, **kwargs)
        if conference is None:
            raise ValueError('conference must be provided')
        self.conference = conference
        self.fields['columns'].initial = [
            self.ORDER_COLUMN, self.ID_COLUMN, self.TITLE_COLUMN,
            self.AUTHORS_COLUMN]

    def apply(self, request):
        submissions = Submission.objects.filter(
            Q(conference=self.conference) &
            Q(status__in=self.cleaned_data['status']))

        order = 0
        result = []
        columns = self.cleaned_data['columns']

        profiles = {
            u.pk: u.profile for u in User.objects.filter(
                authorship__submission__conference=self.conference)
        }
        for sub in submissions:
            order += 1
            record = {}
            authors = sub.authors.all().order_by('order')
            decision = sub.review_decision.first()

            if self.ORDER_COLUMN in columns:
                record[self.ORDER_COLUMN] = order

            if self.ID_COLUMN in columns:
                record[self.ID_COLUMN] = sub.pk

            if self.TITLE_COLUMN in columns:
                record[self.TITLE_COLUMN] = sub.title

            if self.AUTHORS_COLUMN in columns:
                names = [profiles[a.user_id].get_full_name() for a in authors]
                record[self.AUTHORS_COLUMN] = '; '.join(names)

            if self.COUNTRY_COLUMN in columns:
                countries = [
                    profiles[a.user_id].get_country_display() for a in authors]
                countries = list(set(countries))  # remove duplicates
                countries.sort()
                record[self.COUNTRY_COLUMN] = '; '.join(countries)

            if self.STYPE_COLUMN in columns:
                record[self.STYPE_COLUMN] = (
                    sub.stype.get_language_display() if sub.stype else '')

            if self.REVIEW_PAPER_COLUMN in columns:
                record[self.REVIEW_PAPER_COLUMN] = request.build_absolute_uri(
                    reverse('submissions:download-manuscript', args=[sub.pk]))

            if self.REVIEW_SCORE_COLUMN in columns:
                score = get_average_score(sub)
                score_string = f'{score:.1f}' if score else '-'
                record[self.REVIEW_SCORE_COLUMN] = score_string

            if self.STATUS_COLUMN in columns:
                record[self.STATUS_COLUMN] = sub.get_status_display()

            if self.TOPICS_COLUMN in columns:
                record[self.TOPICS_COLUMN] = '; '.join(sub.topics.values_list(
                    'name', flat=True))

            if self.PTYPE_COLUMN in columns:
                record[self.PTYPE_COLUMN] = (
                    decision.proc_type.name if (decision and decision.proc_type)
                    else '')

            if self.VOLUME_COLUMN in columns:
                record[self.VOLUME_COLUMN] = (
                    decision.volume.name if (decision and decision.volume)
                    else '')

            result.append(record)
        return result


class ExportUsersForm(Form):
    ORDER_COLUMN = '#'
    ID_COLUMN = 'ID'
    FULL_NAME_COLUMN = 'FULL_NAME'
    FULL_NAME_RUS_COLUMN = 'FULL_NAME_RUS'
    DEGREE_COLUMN = 'DEGREE'
    COUNTRY_COLUMN = 'COUNTRY'
    CITY_COLUMN = 'CITY'
    AFFILIATION_COLUMN = 'AFFILIATION'
    ROLE_COLUMN = 'ROLE'
    EMAIL_COLUMN = 'EMAIL'
    NUM_SUBMITTED_COLUMN = 'NUM_SUBMITTED_PAPERS'
    NUM_ACCEPTED_COLUMN = 'NUM_ACCEPTED_PAPERS'

    # noinspection DuplicatedCode
    COLUMNS = (
        (ORDER_COLUMN, ORDER_COLUMN),
        (ID_COLUMN, ID_COLUMN),
        (FULL_NAME_COLUMN, FULL_NAME_COLUMN),
        (FULL_NAME_RUS_COLUMN, FULL_NAME_RUS_COLUMN),
        (DEGREE_COLUMN, DEGREE_COLUMN),
        (COUNTRY_COLUMN, COUNTRY_COLUMN),
        (CITY_COLUMN, CITY_COLUMN),
        (AFFILIATION_COLUMN, AFFILIATION_COLUMN),
        (ROLE_COLUMN, ROLE_COLUMN),
        (EMAIL_COLUMN, EMAIL_COLUMN),
        (NUM_SUBMITTED_COLUMN, NUM_SUBMITTED_COLUMN),
        (NUM_ACCEPTED_COLUMN, NUM_ACCEPTED_COLUMN),
    )

    columns = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False, choices=COLUMNS)

    def __init__(self, *args, conference=None, **kwargs):
        super().__init__(*args, **kwargs)
        if conference is None:
            raise ValueError('conference must be provided')
        self.conference = conference
        self.fields['columns'].initial = [
            self.ORDER_COLUMN, self.ID_COLUMN, self.FULL_NAME_COLUMN]

    # noinspection PyUnusedLocal
    def apply(self, request):
        profiles = Profile.objects.all().order_by('user_id')
        columns = self.cleaned_data['columns']
        emails = {u.pk: u.email for u in User.objects.all()} \
            if self.EMAIL_COLUMN in columns else {}

        submissions = Submission.objects.filter(conference=self.conference)

        order = 0
        result = []

        for pr in profiles:
            order += 1
            record = {}

            if self.ORDER_COLUMN in columns:
                record[self.ORDER_COLUMN] = order

            if self.ID_COLUMN in columns:
                record[self.ID_COLUMN] = pr.user_id

            if self.FULL_NAME_COLUMN in columns:
                record[self.FULL_NAME_COLUMN] = pr.get_full_name()

            if self.FULL_NAME_RUS_COLUMN in columns:
                record[self.FULL_NAME_RUS_COLUMN] = ' '.join((
                    pr.first_name_rus, pr.middle_name_rus, pr.last_name_rus))

            if self.DEGREE_COLUMN in columns:
                record[self.DEGREE_COLUMN] = pr.get_degree_display()

            if self.COUNTRY_COLUMN in columns:
                record[self.COUNTRY_COLUMN] = pr.get_country_display()

            if self.CITY_COLUMN in columns:
                record[self.CITY_COLUMN] = pr.city

            if self.AFFILIATION_COLUMN in columns:
                record[self.AFFILIATION_COLUMN] = pr.affiliation

            if self.ROLE_COLUMN in columns:
                record[self.ROLE_COLUMN] = pr.get_role_display()

            if self.EMAIL_COLUMN in columns:
                record[self.EMAIL_COLUMN] = emails.get(pr.user_id, '')

            if self.NUM_SUBMITTED_COLUMN in columns:
                record[self.NUM_SUBMITTED_COLUMN] = submissions.filter(
                    authors__user=pr.user_id).count()

            if self.NUM_ACCEPTED_COLUMN in columns:
                record[self.NUM_ACCEPTED_COLUMN] = submissions.filter(
                    Q(authors__user=pr.user_id) & Q(status__in=[
                        Submission.ACCEPTED, Submission.IN_PRINT,
                        Submission.PUBLISHED])).count()

            result.append(record)
        return result
