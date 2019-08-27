from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models import Model, CharField, ForeignKey, CASCADE, SET_NULL, \
    BooleanField
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from conferences.models import Conference, ProceedingType, ProceedingVolume
from submissions.models import Submission
from users.models import User


# Create your models here.
class Reviewer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
        ('', _('Choose your score')),
        (str(POOR), _('1 - Very Poor')),
        (str(BELOW_AVERAGE), _('2 - Below Average')),
        (str(AVERAGE), _('3 - Average')),
        (str(GOOD), _('4 - Good')),
        (str(EXCELLENT), _('5 - Excellent'))
    )

    reviewer = models.ForeignKey(
        Reviewer,
        on_delete=models.CASCADE,
        related_name='reviews',
    )

    paper = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name='reviews',
    )

    technical_merit = models.CharField(
        choices=SCORE_CHOICES,
        max_length=1,
        blank=True,
    )

    clarity = models.CharField(
        choices=SCORE_CHOICES,
        max_length=1,
        blank=True,
    )

    relevance = models.CharField(
        choices=SCORE_CHOICES,
        max_length=1,
        blank=True,
    )

    originality = models.CharField(
        choices=SCORE_CHOICES,
        max_length=1,
        blank=True,
    )

    details = models.TextField()

    submitted = models.BooleanField(default=False)

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
        return tuple(k for k, v in self.score_fields().items() if v == '')

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
        if self.all_scores_filled():
            fields = self.score_fields()
            return sum(int(x) for x in fields.values()) / len(fields)
        return 0


def check_review_details(value, submission_type):
    num_words = len(value.split())
    return num_words >= submission_type.min_num_words_in_review


def _send_email(user, review, subject, template_html, template_plain):
    profile = user.profile
    context = {
        'email': user.email,
        'first_name': profile.first_name,
        'last_name': profile.last_name,
        'review': review,
        'protocol': settings.SITE_PROTOCOL,
        'domain': settings.SITE_DOMAIN,
        'deadline': review.paper.conference.review_stage.end_date,
    }
    html = render_to_string(template_html, context)
    text = render_to_string(template_plain, context)
    send_mail(subject, message=text, html_message=html,
              recipient_list=[user.email],
              from_email=settings.DEFAULT_FROM_EMAIL, fail_silently=False)


@receiver(post_save, sender=Review)
def create_review(sender, instance, created, **kwargs):
    if created:
        assert isinstance(instance, Review)
        _send_email(
            instance.reviewer.user, instance,
            f"[DCCN2019] Review assignment for submission #{instance.paper.pk}",
            template_html='review/email/start_review.html',
            template_plain='review/email/start_review.txt')


@receiver(post_delete, sender=Review)
def delete_review(sender, instance, **kwargs):
    _send_email(
        instance.reviewer.user, instance,
        f"[DCCN2019] Review cancelled for submission #{instance.paper.pk}",
        template_html='review/email/cancel_review.html',
        template_plain='review/email/cancel_review.txt')


class Decision(Model):
    UNDEFINED = 'UNDEFINED'
    ACCEPT = 'ACCEPT'
    REJECT = 'REJECT'

    DECISION_CHOICES = (
        (UNDEFINED, 'No decision'),
        (ACCEPT, 'Accept submission'),
        (REJECT, 'Reject submission')
    )

    decision = CharField(choices=DECISION_CHOICES, default=UNDEFINED,
                         max_length=10)
    submission = ForeignKey(Submission, on_delete=CASCADE,
                            related_name='review_decision')
    proc_type = ForeignKey(ProceedingType, on_delete=SET_NULL, null=True,
                           blank=True)
    volume = ForeignKey(ProceedingVolume, on_delete=SET_NULL, null=True,
                        blank=True)
    committed = BooleanField(default=False)

    def commit(self, silent=False):
        """Change submission status depending on decision.

        - if decision is UNDEFINED, submission will go to REVIEW state;
        - if decision is ACCEPT, submission will go to ACCEPTED state;
        - if decision is REJECT, submission will go to REJECTED state.

        If submission status was already IN_PRINT, it won't be changed.
        """
        if self.committed:
            return   # do nothing if already committed
        status = self.submission.status
        # Update submission status if needed
        decision_status = {
            Decision.UNDEFINED: Submission.UNDER_REVIEW,
            Decision.ACCEPT: Submission.ACCEPTED,
            Decision.REJECT: Submission.REJECTED,
        }
        if status != Submission.IN_PRINT:
            new_status = decision_status[self.decision]
            update_status = status != new_status
            self.submission.status = new_status
            # TODO: either here, or in submission.save() add/del Contribution
            self.submission.save()
            if update_status and self.decision != Decision.UNDEFINED:
                # TODO: inform user about proc_type or volume change
                # (we are here if status didn't change, so Submission.save()
                # will not emit an email due to status change; so we need to
                # inform user manually)
                if not silent:
                    pass
        self.committed = True
        self.save()

    def save(self, *args, **kwargs):
        old = Decision.objects.filter(pk=self.pk).first()
        if old:
            fields = ['decision', 'volume', 'proc_type']
            for field in fields:
                if getattr(self, field) != getattr(old, field):
                    self.committed = False
                    print('found changed field')
                    break
        super().save(*args, **kwargs)
