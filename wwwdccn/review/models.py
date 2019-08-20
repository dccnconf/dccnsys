from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from conferences.models import Conference
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


@receiver(post_save, sender=Review)
def create_review(sender, instance, created, **kwargs):
    if created:
        assert isinstance(instance, Review)
        user = instance.reviewer.user
        profile = user.profile
        context = {
            'email': user.email,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'review': instance,
            'protocol': settings.SITE_PROTOCOL,
            'domain': settings.SITE_DOMAIN,
            'deadline': instance.paper.conference.review_stage.end_date,
        }
        html = render_to_string('review/email/start_review.html', context)
        text = render_to_string('review/email/start_review.txt', context)
        send_mail(
            f"[DCCN2019] Review assignment for submission #{instance.paper.pk}",
            message=text,
            html_message=html,
            recipient_list=[user.email],
            from_email=settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
        )


@receiver(post_delete, sender=Review)
def delete_review(sender, instance, **kwargs):
    user = instance.reviewer.user
    profile = user.profile
    context = {
        'email': user.email,
        'first_name': profile.first_name,
        'last_name': profile.last_name,
        'review': instance,
        'protocol': settings.SITE_PROTOCOL,
        'domain': settings.SITE_DOMAIN,
        'deadline': instance.paper.conference.review_stage.end_date,
    }
    html = render_to_string('review/email/cancel_review.html', context)
    text = render_to_string('review/email/cancel_review.txt', context)
    send_mail(
        f"[DCCN2019] Review cancelled for submission #{instance.paper.pk}",
        message=text,
        html_message=html,
        recipient_list=[user.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
        fail_silently=False,
    )
