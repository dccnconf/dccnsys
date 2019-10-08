import statistics

from django.db import models
from django.db.models import Model, CharField, ForeignKey, CASCADE, SET_NULL, \
    IntegerField, FloatField, OneToOneField, ManyToManyField
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from conferences.models import Conference, ProceedingType, ProceedingVolume, \
    ArtifactDescriptor
from submissions.models import Submission
from users.models import User


class ReviewStage(Model):
    submission = models.ForeignKey(Submission, on_delete=SET_NULL, null=True)
    num_reviews_required = models.IntegerField()
    score = models.FloatField(null=True, blank=True, default=None)
    locked = models.BooleanField(default=False)

    def get_num_missing_reviews(self):
        return max(0, self.num_reviews_required - self.review_set.count())

    def update_score(self, commit=True):
        scores = [review.average_score() for review in self.review_set.all()]
        scores = [x for x in scores if x]
        prev_score = self.score
        new_score = sum(scores) / len(scores) if scores else None
        self.score = new_score
        if commit and prev_score != new_score:
            self.save()

    @property
    def decision_type(self):
        if not hasattr(self, 'decision'):
            return None
        return self.decision.decision_type


@receiver(post_save, sender=Submission)
def create_review_stage(**kwargs):
    """When submission status is UNDER_REVIEW, we create a ReviewStage for it.
    """
    submission = kwargs.get('instance')
    if (submission.status == Submission.UNDER_REVIEW and
            submission.reviewstage_set.count() == 0):
        sub_type = submission.stype
        num_reviews_required = sub_type.num_reviews if sub_type else 0
        ReviewStage.objects.create(
            submission=submission, num_reviews_required=num_reviews_required,
            locked=False)


@receiver(post_save, sender=Submission)
def update_review_stage_lock(**kwargs):
    submission = kwargs.get('instance')
    stage = submission.reviewstage_set.first()
    if submission.status in [Submission.ACCEPTED, Submission.REJECTED]:
        if stage and not stage.locked:
            stage.locked = True
            stage.save()
    elif submission.status == Submission.UNDER_REVIEW:
        if stage and stage.locked:
            stage.locked = False
            stage.save()


# Create your models here.
class Reviewer(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)


SCORE = (
    ('1', _('1 - Very Poor')),
    ('2', _('2 - Below Average')),
    ('3', _('3 - Average')),
    ('4', _('4 - Good')),
    ('5', _('5 - Excellent')),
)


class Review(models.Model):
    NUM_SCORES = 4

    # Score choices codes:
    POOR = 1
    BELOW_AVERAGE = 2
    AVERAGE = 3
    GOOD = 4
    EXCELLENT = 5

    SCORE_CHOICES = (
        (None, _('Choose your score')),
        (POOR, _('1 - Very Poor')),
        (BELOW_AVERAGE, _('2 - Below Average')),
        (AVERAGE, _('3 - Average')),
        (GOOD, _('4 - Good')),
        (EXCELLENT, _('5 - Excellent'))
    )

    reviewer = models.ForeignKey(
        Reviewer,
        on_delete=models.CASCADE,
        related_name='reviews',
    )

    stage = models.ForeignKey(
        ReviewStage, blank=True, default=None, on_delete=SET_NULL, null=True)

    locked = models.BooleanField(default=False)

    technical_merit = models.IntegerField(
        choices=SCORE_CHOICES, default=None, blank=True, null=True)
    clarity = models.IntegerField(
        choices=SCORE_CHOICES, default=None, blank=True, null=True)
    relevance = models.IntegerField(
        choices=SCORE_CHOICES, default=None, blank=True, null=True)
    originality = models.IntegerField(
        choices=SCORE_CHOICES, default=None, blank=True, null=True)

    details = models.TextField()

    submitted = models.BooleanField(default=False)

    @property
    def paper(self):
        return self.stage.submission

    def __str__(self):
        name = self.reviewer.user.profile.get_full_name()
        return f'Review for submission #{self.paper.pk} by {name}'

    def check_details(self):
        return check_review_details(self.details, self.paper.stype)

    def score_fields(self):
        return {
            'technical_merit': self.technical_merit,
            'clarity': self.clarity,
            'originality': self.originality,
            'relevance': self.relevance,
        }

    def missing_score_fields(self):
        return tuple(k for k, v in self.score_fields().items() if v is None)

    def all_scores_filled(self):
        return self.num_scores_missing() == 0

    def num_scores_missing(self):
        return len(self.missing_score_fields())

    def warnings(self):
        num_missing = self.num_scores_missing()
        warnings = []
        if num_missing == Review.NUM_SCORES and not self.details:
            warnings.append('Please, start the review')
        else:
            filled_details = self.check_details()
            filled_scores = num_missing == 0

            if not filled_scores:
                warnings.append(
                    f'{num_missing} of {Review.NUM_SCORES} scores not filled'
                )
            if not filled_details:
                warnings.append('Review details are incomplete')
            if filled_scores and filled_details and not self.submitted:
                warnings.append('Review is not submitted yet')
        return warnings

    def average_score(self):
        fields = self.score_fields()
        values = [x for x in fields.values() if x]
        return sum(values) / len(values) if values else 0


@receiver([post_save, post_delete], sender=Review)
def update_average_score_after_review_save(sender, instance, **kwargs):
    """Whenever a Review is updated or deleted, its owner should
    recompute the average score.
    """
    instance.stage.update_score(commit=True)


@receiver(post_save, sender=ReviewStage)
def update_reviews_lock(**kwargs):
    stage = kwargs.get('instance')
    updated_reviews = []
    for review in stage.review_set.all():
        if review.locked != stage.locked:
            review.locked = stage.locked
            updated_reviews.append(review)
    if updated_reviews:
        Review.objects.bulk_update(updated_reviews, ['locked'])


def check_review_details(value, submission_type):
    num_words = len(value.split())
    return num_words >= submission_type.min_num_words_in_review


class ReviewDecisionType(Model):
    ACCEPT = 'ACCEPT'
    REJECT = 'REJECT'
    CHOICES = ((ACCEPT, 'Accept submission'), (REJECT, 'Reject submission'))

    decision = CharField(choices=CHOICES, default=ACCEPT, max_length=6)
    allowed_proceedings = ManyToManyField(
        ProceedingType, related_name='decision_types')
    description = CharField(blank=True, default='', max_length=1024)
    conference = ForeignKey(Conference, on_delete=CASCADE, null=True,
                            blank=True, default=None)

    class Meta:
        unique_together = ['conference', 'decision', 'description']
        ordering = ['conference_id', 'decision', 'description']


class ReviewDecision(Model):
    decision_type = ForeignKey(
        ReviewDecisionType, on_delete=SET_NULL, related_name='decisions',
        null=True, blank=True, default=None)
    stage = OneToOneField(ReviewStage, on_delete=CASCADE,
                          related_name='decision')

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)
        decision = self.decision_type.decision if self.decision_type else None
        if decision:
            submission = self.stage.submission
            if decision == ReviewDecisionType.ACCEPT:
                submission.status = Submission.ACCEPTED
                submission.save()
            elif decision == ReviewDecisionType.REJECT:
                submission.status = Submission.REJECTED
                submission.save()
        return ret


@receiver(post_save, sender=ReviewStage)
def create_decision_after_stage_created(**kwargs):
    """When ReviewStage is created, a OneToOne field ReviewDecision should
    be also created."""
    review_stage = kwargs['instance']
    if kwargs['created']:
        ReviewDecision.objects.get_or_create(stage=review_stage)


class ReviewStats(Model):
    conference = OneToOneField(Conference, on_delete=CASCADE,
                               related_name='review_stats')

    num_submissions_reviewed = IntegerField(
        default=0,
        verbose_name='Number of submissions with all reviews submitted')

    num_submissions_with_incomplete_reviews = IntegerField(
        default=0,
        verbose_name='Number of submissions with incomplete reviews')

    num_submissions_with_missing_reviewers = IntegerField(
        default=0,
        verbose_name='Number of submissions missing one or more reviewers')

    average_score = FloatField(
        default=0.0,
        verbose_name='Average score over all completely reviewed submissions')

    median_score = FloatField(
        default=0.0,
        verbose_name='Median score over all completely reviewed submissions')

    q1_score = FloatField(
        default=0.0,
        verbose_name='Q1 score (25% are not greater then)')

    q3_score = FloatField(
        default=0.0,
        verbose_name='Q3 score (25% are not less then)')

    def update_stats(self):
        """Compute and record statistics.
        """
        from review.utilities import review_finished, count_required_reviews, \
            get_average_score

        # 1) Count submissions with complete, incomplete and missing reviews
        stype_cache = {
            st.pk: st for st in self.conference.submissiontype_set.all()
        }
        submissions = self.conference.submission_set.exclude(
            status=Submission.SUBMITTED)

        self.num_submissions_reviewed = 0
        self.num_submissions_with_incomplete_reviews = 0
        self.num_submissions_with_missing_reviewers = 0
        for submission in submissions:
            if review_finished(submission, stype_cache):
                self.num_submissions_reviewed += 1
            else:
                stage = submission.reviewstage_set.first()
                if stage.get_num_missing_reviews() > 0:
                    self.num_submissions_with_missing_reviewers += 1
                self.num_submissions_with_incomplete_reviews += 1

        # 2) Compute submission scores:
        self.average_score = get_average_score(submissions)
        self.median_score = 0.0
        self.q1_score = 0.0
        self.q3_score = 0.0
        scores = [get_average_score(submission) for submission in submissions]
        scores = [score for score in scores if score is not None and score > 0]
        if scores:
            self.median_score = statistics.median(scores)
            under_median_scores = [
                score for score in scores if score < self.median_score]
            if under_median_scores:
                self.q1_score = statistics.median(under_median_scores)
            upper_median_scores = [
                score for score in scores if score >= self.median_score]
            if upper_median_scores:
                self.q3_score = statistics.median(upper_median_scores)

        # 3) Save!
        self.save()

    EXCELLENT_QUALITY = 'excellent'
    GOOD_QUALITY = 'good'
    AVERAGE_QUALITY = 'average'
    POOR_QUALITY = 'poor'
    UNKNOWN_QUALITY = ''

    def qualify_score(self, score):
        if not score:
            return ReviewStats.UNKNOWN_QUALITY
        if isinstance(score, str):
            score = float(score)
        if 0 < score < self.q1_score:
            return ReviewStats.POOR_QUALITY
        if 0 < score < self.median_score:
            return ReviewStats.AVERAGE_QUALITY
        if 0 < score < self.q3_score:
            return ReviewStats.GOOD_QUALITY
        if score >= self.q3_score:
            return ReviewStats.EXCELLENT_QUALITY
        return ReviewStats.UNKNOWN_QUALITY


# noinspection PyUnusedLocal
@receiver(post_save, sender=Review)
def update_statistics(sender, instance, **kwargs):
    assert isinstance(instance, Review)
    conference = instance.paper.conference
    stats, _ = ReviewStats.objects.get_or_create(conference=conference)
    stats.update_stats()


# def _send_email(user, review, subject, template_html, template_plain):
#     profile = user.profile
#     context = {
#         'email': user.email,
#         'first_name': profile.first_name,
#         'last_name': profile.last_name,
#         'review': review,
#         'protocol': settings.SITE_PROTOCOL,
#         'domain': settings.SITE_DOMAIN,
#         'deadline': review.paper.conference.review_stage.end_date,
#     }
#     html = render_to_string(template_html, context)
#     text = render_to_string(template_plain, context)
#     send_mail(subject, message=text, html_message=html,
#               recipient_list=[user.email],
#               from_email=settings.DEFAULT_FROM_EMAIL, fail_silently=False)


# # noinspection PyUnusedLocal
# @receiver(post_save, sender=Review)
# def create_review(sender, instance, created, **kwargs):
#     if created:
#         assert isinstance(instance, Review)
#         _send_email(
#             instance.reviewer.user, instance,
#             f"[DCCN2019] Review assignment for submission #{instance.paper.pk}",
#             template_html='review/email/start_review.html',
#             template_plain='review/email/start_review.txt')


# # noinspection PyUnusedLocal
# @receiver(post_delete, sender=Review)
# def delete_review(sender, instance, **kwargs):
#     _send_email(
#         instance.reviewer.user, instance,
#         f"[DCCN2019] Review cancelled for submission #{instance.paper.pk}",
#         template_html='review/email/cancel_review.html',
#         template_plain='review/email/cancel_review.txt')


