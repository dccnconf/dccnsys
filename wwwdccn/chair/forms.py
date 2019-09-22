from functools import reduce

from django import forms
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, F, Count, Max, Subquery, OuterRef, Value
from django.db.models.functions import Concat
from django.forms import MultipleChoiceField, ChoiceField, Form, CharField
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from django_countries import countries

from conferences.models import Conference, ProceedingVolume, ArtifactDescriptor
from gears.widgets import CustomCheckboxSelectMultiple, CustomFileInput
from review.models import Reviewer, Review, Decision, ReviewStats
from review.utilities import get_average_score, count_required_reviews, \
    review_finished
from submissions.models import Submission, Artifact
from users.models import Profile

User = get_user_model()


# noinspection PyUnusedLocal
def clean_data_to_int(iterable, empty=None):
    return [int(x) if x != '' else None for x in iterable]


def q_or(disjuncts, default=True):
    if disjuncts:
        return reduce(lambda acc, d: acc | d, disjuncts)
    return Q(pk__isnull=(not default))  # otherwise, check whether PK is null


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
    COMPLETE_SUBMISSION = 'COMPLETE'
    MISSING_TITLE = 'MISSING_TITLE'
    NO_REVIEW_MANUSCRIPT = 'NO_REVIEW_PDF'
    INCOMPLETE_REVIEWS = 'INCOMPLETE_REVIEWS'
    UNASSIGNED_REVIEWERS = 'UNASSIGNED_REVIEWERS'
    MISSING_ARTIFACT = 'MISSING_MANDATORY_ART'
    MISSING_OPT_ARTIFACT = 'MISSING_OPT_ART'
    COMPLETION_CHOICES = (
        (COMPLETE_SUBMISSION, 'Everything complete'),
        (MISSING_TITLE, 'Empty submissions'),
        (NO_REVIEW_MANUSCRIPT, 'Missing review PDF'),
        (INCOMPLETE_REVIEWS, 'Incomplete reviews'),
        (UNASSIGNED_REVIEWERS, 'Unassigned reviewers'),
        (MISSING_ARTIFACT, 'Missing mandatory artifacts'),
        (MISSING_OPT_ARTIFACT, 'Missing optional artifacts'),
    )

    Q1 = 'Q1'
    Q2 = 'Q2'
    Q3 = 'Q3'
    Q4 = 'Q4'
    QUARTILE_CHOICES = ((Q1, 'Q1'), (Q2, 'Q2'), (Q3, 'Q3'), (Q4, 'Q4'))

    ORDER_BY_PK = 'PK'
    ORDER_BY_TITLE = 'TITLE'
    ORDER_BY_SCORE = 'SCORE'
    ORDER_CHOICES = (
        (ORDER_BY_PK, 'Order by ID'),
        (ORDER_BY_SCORE, 'Order by score'),
        (ORDER_BY_TITLE, 'Order by title'),
    )

    DIRECTION_CHOICES = (('ASC', 'Ascending'), ('DESC', 'Descending'))

    class Meta:
        model = Conference
        fields = []

    term = forms.CharField(required=False)

    completion = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple(attrs={
            'btn_class': 'btn btn-link dccn-link dccn-text-small',
            'label_class': 'dccn-text-0',
        }), required=False, choices=COMPLETION_CHOICES)

    types = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False)

    topics = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False)

    status = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=Submission.STATUS_CHOICE)

    countries = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False)

    affiliations = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False)

    proc_types = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple(
            attrs={'label': 'Proceedings'}), required=False)

    volumes = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False)

    quartiles = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=QUARTILE_CHOICES)

    artifacts = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False)

    order = ChoiceField(required=False, choices=ORDER_CHOICES)
    direction = ChoiceField(required=False, choices=DIRECTION_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self.instance, Conference)
        self.fields['types'].choices = [
            (x.pk, x.name) for x in self.instance.submissiontype_set.all()]
        self.fields['topics'].choices = [
            (x.pk, x.name) for x in self.instance.topic_set.all()]
        self.fields['proc_types'].choices = [('', 'Not defined')] + [
            (x.pk, x.name) for x in self.instance.proceedingtype_set.all()]
        self.fields['volumes'].choices = [('', 'Not defined')] + [
            (vol_pk, vol_name) for (vol_pk, vol_name) in
            self.instance.proceedingtype_set.values_list(
                'volumes__pk', 'volumes__name').distinct()]
        self.fields['artifacts'].choices = [
            (x.pk, f'{x.name} ({x.proc_type.name}') for x in
            ArtifactDescriptor.objects.filter(
                 proc_type__conference=self.instance)]

        profiles_data = Profile.objects.filter(
            user__authorship__submission__conference=self.instance).values(
            'affiliation', 'country')
        self.fields['countries'].choices = [
            (x, dict(countries)[x]) for x in profiles_data.values_list(
                'country', flat=True).distinct().order_by('country')]
        self.fields['affiliations'].choices = [
            (x, x) for x in profiles_data.values_list(
                'affiliation', flat=True).distinct().order_by('affiliation')]

        self.conjuncts = []

    def order_submissions(self, submissions):
        order = self.cleaned_data['order']
        direction = '' if self.cleaned_data['direction'] == 'ASC' else '-'
        if order == self.ORDER_BY_PK:
            return submissions.order_by(f'{direction}pk')

        elif order == self.ORDER_BY_TITLE:
            return submissions.order_by(f'{direction}title')

        elif order == self.ORDER_BY_SCORE:
            #FIXME: refactor this to use pure SQL instead of Python:
            max_pk = max(submissions.aggregate(Max('pk'))['pk__max'], 1)

            def order_key(sub):
                score = get_average_score(sub)
                v = (-score, sub.pk / max_pk)
                return sum(x * 10**(len(v)-1-i) for i, x in enumerate(v))

            ordered_submissions = list(submissions)
            ordered_submissions.sort(key=order_key, reverse=(direction == '-'))
            return ordered_submissions

        return submissions

    def clean_completion(self):
        data = self.cleaned_data['completion']
        disjuncts = []

        # Below we define various queries for _non-empty_ submissions those
        # may be issued within 'completion' choice. Negation of these
        # queries conjunction along with condition on non-emptiness give
        # complete submission criterion:
        queries = {
            self.NO_REVIEW_MANUSCRIPT:
                Q(review_manuscript='') & Q(status=Submission.SUBMITTED),
            self.UNASSIGNED_REVIEWERS:
                Q(num_reviews_assigned__lt=F('num_reviews_required')) &
                Q(status=Submission.UNDER_REVIEW),
            self.INCOMPLETE_REVIEWS:
                Q(num_reviews_submitted__lt=F('num_reviews_assigned')) &
                Q(status=Submission.UNDER_REVIEW),
            self.MISSING_ARTIFACT:
                Q(num_missing_mandatory_artifacts__gt=0) &
                Q(status=Submission.ACCEPTED),
            self.MISSING_OPT_ARTIFACT:
                Q(num_missing_optional_artifacts__gt=0) &
                Q(status=Submission.ACCEPTED),
        }

        empty = Q(title='')  # we use this often below
        if self.MISSING_TITLE in data:
            disjuncts.append(empty)

        # Check every option defined in queries dictionary above. Disjunct
        # all presented in 'completion' choice options, conjunct them with
        # non-emptiness and add to 'disjuncts' list (~E & (Q1 | Q2 | ... | Qn))
        non_empty_disjuncts = []
        for opt, query in queries.items():
            if opt in data:
                non_empty_disjuncts.append(query)
        if non_empty_disjuncts:
            disjuncts.append(
                ~empty & reduce(lambda q, acc: acc | q, non_empty_disjuncts))

        # If we are also interested in completed submissions, disjuct all
        # queries defined above (regardless of whether they are presented
        # in completion choices!), conjunct with non-emptiness and put to
        # 'disjuncts' list:
        if self.COMPLETE_SUBMISSION in data:
            disjuncts.append(
                ~empty & ~reduce(lambda q, acc: acc | q, queries.values()))

        if disjuncts:
            self.conjuncts.append(reduce(lambda q, acc: acc | q, disjuncts))

        return data

    def clean_topics(self):
        data = self.cleaned_data['types']
        items = [int(topic) for topic in data if topic]
        if items:
            self.conjuncts.append(Q(stype__in=items))
        return data

    def clean_status(self):
        data = self.cleaned_data['status']
        if data:
            self.conjuncts.append(Q(status__in=data))
        return data

    def clean_countries(self):
        data = self.cleaned_data['countries']
        if data:
            self.conjuncts.append(Q(authors__user__profile__country__in=data))
        return data

    def clean_affiliations(self):
        data = self.cleaned_data['affiliations']
        if data:
            self.conjuncts.append(
                Q(authors__user__profile__affiliation__in=data))
        return data

    # noinspection DuplicatedCode
    def clean_proc_types(self):
        data = self.cleaned_data['proc_types']
        disjuncts = []
        proc_types = [int(x) for x in data if x]
        if proc_types:
            disjuncts.append(Q(review_decision__proc_type__in=proc_types))
        if '' in data:
            disjuncts.append(Q(review_decision__proc_type=None))
        if disjuncts:
            self.conjuncts.append(reduce(lambda q, acc: acc | q, disjuncts))
        return data

    # noinspection DuplicatedCode
    def clean_volumes(self):
        data = self.cleaned_data['volumes']
        disjuncts = []
        volumes = [int(x) for x in data if x]
        if volumes:
            disjuncts.append(Q(review_decision__volume__in=volumes))
        if '' in data:
            disjuncts.append(Q(review_decision__volume=None))
        if disjuncts:
            self.conjuncts.append(reduce(lambda q, acc: acc | q, disjuncts))
        return data

    def clean_quartiles(self):
        data = self.cleaned_data['quartiles']
        # Since the following computations are expensive, do them only when
        # we need them. Also skip if no review stats are available:
        stats_query = ReviewStats.objects.filter(conference=self.instance)
        if not data or not stats_query.count():
            return data

        stats = stats_query.first()
        q1, q2, q3 = stats.q1_score, stats.median_score, stats.q3_score

        # We also make sure that review stats were filled, since otherwise
        # the following code may raise errors, while there won't be any
        # results:
        if not stats.median_score:
            # TODO: maybe add Q(pk__isnull=True) to conjuncts:
            # this will make result always empty -- if there is no median
            # (so Q1 and Q2), checking any quartile will result in empty set.
            return data

        submissions = Submission.objects.filter(status__in=[
            Submission.UNDER_REVIEW, Submission.ACCEPTED, Submission.REJECTED,
            Submission.IN_PRINT, Submission.PUBLISHED])
        scores = {sub: get_average_score(sub) for sub in submissions}
        # Skip all submissions without average score:
        submissions = [sub for sub in submissions if scores[sub]]
        disjuncts = []
        if self.Q1 in data:
            disjuncts.append(lambda sub: scores[sub] < q1)
        if self.Q2 in data:
            disjuncts.append(lambda sub: q1 <= scores[sub] < q2)
        if self.Q3 in data:
            disjuncts.append(lambda sub: q2 <= scores[sub] < q3)
        if self.Q4 in data:
            disjuncts.append(lambda sub: q3 <= scores[sub])
        submissions = [sub for sub in submissions
                       if any(predicate(sub) for predicate in disjuncts)]
        self.conjuncts.append(Q(pk__in=[sub.pk for sub in submissions]))
        return data

    def clean_artifacts(self):
        data = self.cleaned_data['artifacts']
        disjuncts = []
        descriptors = [int(x) for x in data if x]
        for desc_pk in descriptors:
            disjuncts.append(Q(artifacts__in=Subquery(
                Artifact.objects.filter(
                    descriptor=desc_pk, submission=OuterRef('pk')
                ).exclude(file='').values('pk')),
                review_decision__proc_type__artifacts=desc_pk))
        if disjuncts:
            self.conjuncts.append(reduce(lambda q, acc: acc | q, disjuncts))
        return data

    def clean_term(self):
        term = self.cleaned_data['term']
        for word in term.lower().split():
            self.conjuncts.append(
                Q(title__icontains=word) | Q(pk__icontains=word) |
                Q(authors__user__profile__first_name__icontains=word) |
                Q(authors__user__profile__last_name__icontains=word) |
                Q(authors__user__profile__first_name_rus__icontains=word) |
                Q(authors__user__profile__middle_name_rus__icontains=word) |
                Q(authors__user__profile__last_name_rus__icontains=word)
            )

    def apply(self, submissions):
        # First, we prepare submissions by annotating them with:
        # - num_reviews_required
        # - num_reviews_assigned
        # - num_reviews_submitted
        # - num_missing_mandatory_artifacts
        # - num_missing_optional_artifacts
        submissions = submissions.annotate(
            num_reviews_required=F('stype__num_reviews'),
            num_reviews_assigned=Count('reviews', distinct=True),
            num_reviews_submitted=Count('reviews', filter=Q(
                reviews__submitted=True), distinct=True),
            num_missing_mandatory_artifacts=Count('artifacts', filter=Q(
                artifacts__file='', artifacts__descriptor__mandatory=True,
                artifacts__descriptor__proc_type=F(
                    'review_decision__proc_type')), distinct=True),
            num_missing_optional_artifacts=Count('artifacts', filter=Q(
                artifacts__file='', artifacts__descriptor__mandatory=False,
                artifacts__descriptor__proc_type=F(
                    'review_decision__proc_type')), distinct=True),
        )

        # Secondly, we build the query from conjuncts and apply the filter:
        for q in self.conjuncts:
            submissions = submissions.filter(q)

        # Finally, distinct results and order them:
        return self.order_submissions(submissions.distinct())


class FilterProfilesForm(forms.ModelForm):
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
    IEEE_MEMBER_COLUMN = 'IEEE_MEMBER'
    STUDENT_COLUMN = 'STUDENT'

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
        (IEEE_MEMBER_COLUMN, IEEE_MEMBER_COLUMN),
        (STUDENT_COLUMN, STUDENT_COLUMN),
    )

    NOT_AUTHOR = 'NO_PAPERS'
    AUTHOR = 'AUTHOR'
    SOLO_AUTHOR = 'SOLO_AUTHOR'
    AUTHORSHIP_CHOICES = (
        (NOT_AUTHOR, 'No submissions'),
        (AUTHOR, 'Has 1 or more submission'),
        (SOLO_AUTHOR, 'Has submissions where he or she is a single author')
    )

    STUDENT = 'YES'
    NOT_STUDENT = 'NO'
    GRADUATION_CHOICES = (
        (STUDENT, 'Students'),
        (NOT_STUDENT, 'Graduated')
    )

    MEMBERSHIP_NONE = 'NONE'
    MEMBERSHIP_IEEE = 'IEEE'
    MEMBERSHIP_CHOICES = (
        (MEMBERSHIP_NONE, 'No memberships'),
        (MEMBERSHIP_IEEE, 'IEEE member'),
    )

    ORDER_BY_ID = 'ID'
    ORDER_BY_NAME = 'NAME'
    ORDER_CHOICES = (
        (ORDER_BY_ID, 'Order by ID'),
        (ORDER_BY_NAME, 'Order by name'),
    )

    DIRECTION_CHOICES = (('ASC', 'Ascending'), ('DESC', 'Descending'))

    class Meta:
        model = Conference
        fields = []

    term = forms.CharField(required=False)

    authorship = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=AUTHORSHIP_CHOICES,
    )

    countries = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    affiliations = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
    )

    graduation = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=GRADUATION_CHOICES,
    )

    membership = forms.MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple, required=False,
        choices=MEMBERSHIP_CHOICES,
    )

    order = ChoiceField(required=False, choices=ORDER_CHOICES)
    direction = ChoiceField(required=False, choices=DIRECTION_CHOICES)

    columns = forms.MultipleChoiceField(
        required=False, choices=COLUMNS,
        widget=CustomCheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self.instance, Conference)
        countries_dict = dict(countries)

        self.fields['countries'].choices = [
            (code, countries_dict[code]) for code in
            Profile.objects.filter(country__isnull=False).values_list(
                'country', flat=True).order_by('country').distinct()]

        self.fields['affiliations'].choices = [
            (aff, aff) for aff in
            Profile.objects.values_list('affiliation', flat=True).order_by(
                'affiliation').distinct() if aff]

    def order_profiles(self, profiles):
        order = self.cleaned_data['order']
        direction = '-' if self.cleaned_data['direction'] == 'DESC' else ''
        if order == self.ORDER_BY_ID or not order:
            return profiles.order_by(f'{direction}pk')

        elif order == self.ORDER_BY_NAME:
            profiles = profiles.annotate(
                full_name=Concat(
                    'last_name', Value(' '), 'first_name',
                    output_field=models.CharField()))
            return profiles.order_by(f'{direction}full_name')

        return profiles

    def apply_term(self, profiles):
        term = self.cleaned_data['term']
        for word in term.lower().split():
            profiles = profiles.filter(
                Q(pk__icontains=word) | Q(first_name__icontains=word) |
                Q(last_name__icontains=word) |
                Q(first_name_rus__icontains=word) |
                Q(last_name_rus__icontains=word) |
                Q(middle_name_rus__icontains=word))
        return profiles

    def apply_countries(self, profiles):
        data = self.cleaned_data['countries']
        if data:
            profiles = profiles.filter(country__in=data)
        return profiles

    def apply_affiliations(self, profiles):
        data = self.cleaned_data['affiliations']
        if data:
            profiles = profiles.filter(affiliation__in=data)
        return profiles

    def apply_authorship(self, profiles):
        data = self.cleaned_data['authorship']
        if not data:
            return profiles

        disjuncts = []  # <-- we store conditions as Q-expressions here
        profiles = profiles.annotate(
            num_submissions=Count('user__authorship', filter=Q(
                user__authorship__submission__conference=self.instance
            ), distinct=True),
        )

        if self.NOT_AUTHOR in data:
            disjuncts.append(Q(num_submissions=0))
        if self.AUTHOR in data:
            disjuncts.append(Q(num_submissions__gt=0))
        if self.SOLO_AUTHOR in data:
            disjuncts.append(Q(
                user__authorship__submission__in=Submission.objects.annotate(
                    num_authors=Count('authors__pk')
                ).filter(num_authors=1, title__gt='')))

        return profiles.filter(q_or(disjuncts)).distinct()

    def apply_graduation(self, profiles):
        data = self.cleaned_data['graduation']
        if not data:
            return profiles
        disjuncts = []
        if self.STUDENT in data:
            disjuncts.append(Q(role__in=Profile.STUDENT_ROLES))
        if self.NOT_STUDENT in data:
            disjuncts.append(~Q(role__in=Profile.STUDENT_ROLES))
        return profiles.filter(q_or(disjuncts))

    def apply_membership(self, profiles):
        data = self.cleaned_data['membership']
        if not data:
            return profiles
        disjuncts = []
        if self.MEMBERSHIP_NONE in data:
            disjuncts.append(Q(ieee_member=False))
        if self.MEMBERSHIP_IEEE in data:
            disjuncts.append(Q(ieee_member=True))
        return profiles.filter(q_or(disjuncts))

    def apply(self, profiles):
        profiles = self.apply_countries(profiles)
        profiles = self.apply_affiliations(profiles)
        profiles = self.apply_authorship(profiles)
        profiles = self.apply_graduation(profiles)
        profiles = self.apply_membership(profiles)
        profiles = self.apply_term(profiles)
        profiles = self.order_profiles(profiles)
        return profiles


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

    columns = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple(hide_apply_btn=True),
        required=False, choices=COLUMNS)

    status = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple(hide_apply_btn=True),
        required=False, choices=Submission.STATUS_CHOICE)

    countries = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple(hide_apply_btn=True),
        required=False)

    topics = MultipleChoiceField(
        widget=CustomCheckboxSelectMultiple(hide_apply_btn=True),
        required=False)

    def __init__(self, *args, conference=None, **kwargs):
        super().__init__(*args, **kwargs)
        if conference is None:
            raise ValueError('conference must be provided')
        self.conference = conference
        self.fields['columns'].initial = [
            self.ORDER_COLUMN, self.ID_COLUMN, self.TITLE_COLUMN,
            self.AUTHORS_COLUMN, self.STATUS_COLUMN]
        countries_list = list(
            set(p.country for p in Profile.objects.all() if p.country))
        countries_list.sort(key=lambda cnt: cnt.name)
        self.fields['countries'].choices = [
            (cnt.code, cnt.name) for cnt in countries_list]
        self.fields['topics'].choices = [
            (t.pk, t.name) for t in self.conference.topic_set.all()]

    def apply(self, request):
        submissions = Submission.objects.filter(conference=self.conference)
        if self.cleaned_data['status']:
            submissions = submissions.filter(
                status__in=self.cleaned_data['status'])
        if self.cleaned_data['countries']:
            submissions = submissions.filter(
                authors__user__profile__country__in=
                self.cleaned_data['countries'])
        if self.cleaned_data['topics']:
            submissions = submissions.filter(
                topics__in=[int(t) for t in self.cleaned_data['topics']])
        submissions = submissions.distinct().order_by('pk')

        order = 0
        result = []
        columns = self.cleaned_data['columns']

        profiles = {
            u.pk: u.profile for u in User.objects.filter(
                authorship__submission__conference=self.conference)
        }

        def get_user_name(profile):
            return f'{profile.last_name} {profile.first_name}'

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
                names = [get_user_name(profiles[a.user_id]) for a in authors]
                record[self.AUTHORS_COLUMN] = '; '.join(names)

            if self.COUNTRY_COLUMN in columns:
                countries_list = [
                    profiles[a.user_id].get_country_display() for a in authors]
                countries_list = list(set(countries_list))  # remove duplicates
                countries_list.sort()
                record[self.COUNTRY_COLUMN] = '; '.join(countries_list)

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
