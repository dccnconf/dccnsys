import os

from django.conf import settings
from django.db.models import Model, ForeignKey, CASCADE
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.db import models

from conferences.models import Topic, SubmissionType, Conference, \
    ArtifactDescriptor

User = get_user_model()


TITLE_MAX_LENGTH = 250
ABSTRACT_MAX_LENGTH = 2500  # 250 words


def get_review_manuscript_full_path(instance, filename):
    ext = filename.split('.')[-1]
    root = settings.MEDIA_PRIVATE_ROOT
    cpk = instance.conference.pk if instance.conference else 'unknown_conf'
    path = f'{root}/{cpk}/submissions'
    name = f'SID{instance.pk:05d}'
    return f'{path}/{name}.{ext}'


class Submission(models.Model):
    SUBMITTED = 'SUBMIT'
    UNDER_REVIEW = 'REVIEW'
    REJECTED = 'REJECT'
    ACCEPTED = 'ACCEPT'
    IN_PRINT = 'PRINT'
    PUBLISHED = 'PUBLISH'

    STATUS_CHOICE = (
        (SUBMITTED, _('Submitted')),
        (UNDER_REVIEW, _('Review')),
        (REJECTED, _('Rejected')),
        (ACCEPTED, _('Accepted')),
        (IN_PRINT, _('In-print')),
        (PUBLISHED, _('Published')),
    )

    conference = models.ForeignKey(
        Conference,
        on_delete=models.SET_NULL,
        null=True,
    )

    title = models.CharField(
        max_length=TITLE_MAX_LENGTH,
        default="",
        verbose_name=_('Title'),
    )

    abstract = models.CharField(
        max_length=ABSTRACT_MAX_LENGTH,
        default="",
        verbose_name=_('Abstract'),
    )

    topics = models.ManyToManyField(
        Topic,
        verbose_name=_('Topics'),
    )

    stype = models.ForeignKey(
        SubmissionType,
        related_name='submissions',
        verbose_name=_('Submission type'),
        on_delete=models.SET_NULL,
        null=True,
    )

    status = models.CharField(
        choices=STATUS_CHOICE,
        default='SUBMIT',
        max_length=10,
    )

    review_manuscript = models.FileField(
        upload_to=get_review_manuscript_full_path,
        blank=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_submissions',
    )

    created_at = models.DateField(
        auto_now_add=True,
    )

    reached_overview = models.BooleanField(default=False)
    filled_details = models.BooleanField(default=False)

    # Authors are filled from Author model

    def save(self, *args, **kwargs):
        from chair_mail.utility import \
            send_submission_status_notification_message
        old = Submission.objects.filter(pk=self.pk).first()
        status_updated = old is None or old.status != self.status
        super().save(*args, **kwargs)
        if status_updated:
            send_submission_status_notification_message(self)

    def __str__(self):
        if not self.title:
            title_prefix = '(no title)'
        else:
            title_prefix = f'"{self.title[:20]}"',
        return f'{self.pk}: {title_prefix}'

    def can_edit_review_manuscript(self):
        return self.status == 'SUBMIT'

    def can_edit_details(self):
        return self.status in {'SUBMIT', 'ACCEPT'}

    def get_review_manuscript_name(self):
        if self.review_manuscript:
            return os.path.basename(self.review_manuscript.file.name)
        return ''

    def is_chaired_by(self, user):
        return user in self.conference.chairs.all()

    def is_author(self, user):
        return bool(self.authors.filter(user=user)) or (self.created_by == user)

    def details_editable_by(self, user):
        return self.is_chaired_by(user) or (
            self.is_author(user) and self.status in {'SUBMIT', 'ACCEPT'}
        )

    def authors_editable_by(self, user):
        return self.is_chaired_by(user) or self.is_author(user)

    def review_manuscript_editable_by(self, user):
        return self.is_chaired_by(user) or (
            self.is_author(user) and self.status == 'SUBMIT'
        )

    def is_viewable_by(self, user):
        return self.is_chaired_by(user) or self.is_author(user)

    def is_manuscript_viewable_by(self, user):
        return (self.is_viewable_by(user) or
                (self.reviews.filter(reviewer__user=user).count() > 0))

    def is_deletable_by(self, user):
        return ((self.is_chaired_by(user) or self.is_author(user))
                and self.status != 'PUBLISH')

    def get_authors_display(self):
        return ', '.join(
            author.user.profile.get_full_name()
            for author in self.authors.order_by('order')
        )

    def warnings(self):
        w = []
        if not self.review_manuscript:
            w.append('Review manuscript missing')
        if not self.title:
            w.append('Missing submission title')
        return w

    def get_authors_profiles(self):
        return tuple(
            author.user.profile for author in self.authors.order_by('order')
        )


class Author(models.Model):
    class Meta:
        ordering = ['order']

    submission = models.ForeignKey(
        Submission,
        related_name='authors',
        on_delete=models.CASCADE
    )

    order = models.IntegerField(default=0)

    user = models.ForeignKey(
        User,
        related_name='authorship',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'Author #{self.pk}: {self.user.profile.get_full_name()}, ' \
            f'submission={self.submission.pk}, order={self.order}'


def get_artifact_full_path(instance, filename):
    ext = filename.split('.')[-1]
    root = settings.MEDIA_PRIVATE_ROOT
    cpk = instance.submission.conference_id if \
        instance.submission and instance.submission.conference \
        else 'unknown_conf'
    code = instance.descriptor.code if \
        instance.descriptor and instance.descriptor.code else 'final'
    path = f'{root}/{cpk}/submissions'
    name = f'SID{instance.pk:05d}_{code}'
    ret = f'{path}/{name}.{ext}'
    return ret


class Artifact(Model):
    class Meta:
        ordering = ['descriptor_id']

    submission = ForeignKey(Submission, related_name='artifacts',
                            on_delete=CASCADE)
    descriptor = ForeignKey(ArtifactDescriptor, related_name='instances',
                            on_delete=CASCADE)
    file = models.FileField(upload_to=get_artifact_full_path, blank=True)

    @property
    def is_active(self):
        decision = self.submission.review_decision.first()
        valid_statuses = {Submission.ACCEPTED, Submission.IN_PRINT,
                          Submission.PUBLISHED}
        if (decision and self.submission.status in valid_statuses
                and decision.decision == decision.ACCEPT):
            return decision.proc_type == self.descriptor.proc_type
        return False

    @property
    def name(self):
        return self.descriptor.name if self.descriptor else ''

    def get_file_name(self):
        if self.file:
            return os.path.basename(self.file.file.name)
        return ''

    def get_chair_download_name(self):
        if self.file:
            original_filename = self.get_file_name()
            ext = original_filename.split('.')[-1]
            code = self.descriptor.code
            print(original_filename, self.submission_id)
            name = f'FIN{self.submission_id:05d}_{code}.{ext}'
            print(name)
            return name
        return ''

    def __str__(self):
        return f'Artifact "{self.name}" of submission #{self.submission_id}'
