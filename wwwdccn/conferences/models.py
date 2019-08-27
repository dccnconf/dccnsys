from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import ForeignKey, CASCADE, CharField, Model, TextField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.db import models

# Create your models here.
from django_countries.fields import CountryField


User = get_user_model()


class Conference(models.Model):
    full_name = models.CharField(
        max_length=300, verbose_name=_('Full name of the conference')
    )

    short_name = models.CharField(
        max_length=30, verbose_name=_('Short name of the conference')
    )

    is_ieee = models.BooleanField(
        default=False, verbose_name=_('The conference is supported by IEEE')
    )

    country = CountryField(null=True, verbose_name=_('Country'))

    city = models.CharField(
        max_length=100, verbose_name=_('City')
    )

    start_date = models.DateField(null=True, verbose_name=_('Opens at'))
    close_date = models.DateField(null=True, verbose_name=_('Closes at'))

    chairs = models.ManyToManyField(User, related_name='chaired_conferences')

    creator = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_conferences'
    )

    logotype = models.ImageField(
        verbose_name=_("Conference logotype"),
        upload_to=f'{settings.MEDIA_PUBLIC_ROOT}/conferences/logo/',
        null=True, blank=True
    )

    description = models.TextField(
        verbose_name=_('Medium length description of the conference'),
        default="",
        blank=True,
    )

    site_url = models.URLField(
        verbose_name=_('Conference informational site'),
        default="",
        blank=True,
    )

    contact_email = models.EmailField(blank=True, default='')

    def __str__(self):
        return f'{self.full_name} ({self.short_name})'


class SubmissionStage(models.Model):
    conference = models.OneToOneField(
        Conference, on_delete=models.CASCADE, related_name='submission_stage'
    )

    end_date = models.DateTimeField(
        null=True, verbose_name=_('Deadline for submissions')
    )

    end_date_description = models.CharField(blank=True, max_length=100)


class ReviewStage(models.Model):
    conference = models.OneToOneField(
        Conference, on_delete=models.CASCADE, related_name='review_stage'
    )

    end_date = models.DateTimeField(
        null=True, verbose_name=_('End of review')
    )


class ProceedingType(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    name = models.CharField(
        max_length=100, verbose_name=_('Short name')
    )

    description = models.CharField(
        max_length=1000, verbose_name=_('Long description')
    )

    final_manuscript_deadline = models.DateTimeField(
        null=True, verbose_name=_('Deadline for final manuscript submission')
    )

    min_num_pages = models.IntegerField(
        default=4, verbose_name=_('Minimum number of pages in submission')
    )

    max_num_pages = models.IntegerField(
        default=4, verbose_name=_('Maximum number of pages in submission')
    )

    final_latex_template = models.FileField(
        null=True, blank=True,
        verbose_name=_('LaTeX template for final manuscript'),
        upload_to=f'{settings.MEDIA_PUBLIC_ROOT}/conferences/templates'
    )

    _final_latex_template_version = models.IntegerField(default=1)

    def __str__(self):
        return self.name


class ProceedingVolume(Model):
    type = ForeignKey(ProceedingType, on_delete=CASCADE, related_name='volumes')
    name = CharField(max_length=256, verbose_name=_('Short name'))
    description = TextField(verbose_name=_('Description'))


class SubmissionType(models.Model):
    LANGUAGES = (
        (None, _('Select submission language')),
        ('RU', _('Russian')),
        ('EN', _('English')),
    )

    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    name = models.CharField(
        max_length=100, verbose_name=_('Short name')
    )

    description = models.CharField(
        max_length=1000, verbose_name=_('Long description')
    )

    language = models.TextField(max_length=2, choices=LANGUAGES)

    latex_template = models.FileField(
        null=True, verbose_name=_('LaTeX template'),
        upload_to=f'{settings.MEDIA_PUBLIC_ROOT}/conferences/templates'
    )

    _latex_template_version = models.IntegerField(default=1)

    num_reviews = models.IntegerField(
        default=2, verbose_name=_('Number of reviews per submission')
    )

    min_num_pages = models.IntegerField(
        default=4, verbose_name=_('Minimum number of pages in submission')
    )

    max_num_pages = models.IntegerField(
        default=4, verbose_name=_('Maximum number of pages in submission')
    )

    blind_review = models.BooleanField(
        default=False, verbose_name=_('Blind review')
    )

    possible_proceedings = models.ManyToManyField(ProceedingType)

    min_num_words_in_review = models.IntegerField(
        default=150, verbose_name=_('Minimum number of words in the review')
    )

    def __str__(self):
        return self.name


class Topic(models.Model):
    class Meta:
        ordering = ['order']

    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    name = models.CharField(max_length=250, verbose_name=_('Topic name'))
    order = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.name}'


@receiver(post_save, sender=Conference)
def create_conference_stages(sender, instance, created, **kwargs):
    if created:
        SubmissionStage.objects.create(conference=instance)
        ReviewStage.objects.create(conference=instance)


@receiver(post_save, sender=Conference)
def save_conference_stages(sender, instance, **kwargs):
    instance.submission_stage.save()
    instance.review_stage.save()
