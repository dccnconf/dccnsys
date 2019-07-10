from django.db import models
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

    def __str__(self):
        name = self.reviewer.user.profile.get_full_name()
        return f'Review for submission #{self.paper.pk} by {name}'
