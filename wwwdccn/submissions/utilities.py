from collections import namedtuple

from django.urls import reverse

from proceedings.models import Artifact
from submissions.models import Submission


def is_authorized_edit(user, submission):
    return submission.is_author(user) or submission.is_chaired_by(user)


def is_authorized_view_attachment(user, submission):
    return submission.is_author(user) or submission.is_chaired_by(user)


_ALL = ('chair', 'author')
_CHAIR_ONLY = ('chair',)
warning_class = namedtuple(
    'Warning', ('label', 'link', 'chair_link', 'visible_by', 'link_label'),
    defaults=['', _ALL, 'view...'])


def list_warnings(submission):
    wc = warning_class

    pk = submission.pk
    url_details = reverse('submissions:details', kwargs={'pk': pk})
    url_review_manuscript = reverse('submissions:edit-manuscript',
                                    kwargs={'pk': pk})
    url_camera_ready = reverse('submissions:camera-ready', kwargs={'pk': pk})
    url_assign_reviewers = reverse('chair:submission-reviewers',
                                   kwargs={'sub_pk': pk})

    assert isinstance(submission, Submission)
    warnings = []
    if not submission.title.strip():
        warnings.append(wc('Missing title', url_details, link_label='edit...'))
    if not submission.abstract.strip():
        warnings.append(wc('Missing abstract', url_details,
                           link_label='edit...'))
    if submission.topics.count() == 0:
        warnings.append(wc('No topics selected', url_details,
                           link_label='select...'))
    if not submission.stype:
        warnings.append(wc('Type not selected', url_details,
                           link_label='select...'))

    if submission.status == Submission.SUBMITTED:
        if not submission.review_manuscript:
            warnings.append(
                wc('Missing review manuscript', url_review_manuscript,
                   link_label='upload...'))

    if submission.status == Submission.UNDER_REVIEW:
        stage = submission.reviewstage_set.first()
        if submission.stype and stage:
            num_not_finished = stage.review_set.filter(submitted=False).count()
            num_missing = stage.get_num_missing_reviews()
            if num_missing > 0:
                warnings.append(wc(
                    f'{num_missing} reviewers not assigned',
                    '', chair_link=url_assign_reviewers, visible_by=_CHAIR_ONLY,
                    link_label='assign...'
                ))
            if num_not_finished > 0:
                warnings.append(wc(
                    f'{num_not_finished} reviews not finished',
                    '', chair_link=url_assign_reviewers, visible_by=_CHAIR_ONLY,
                ))

    if submission.status == Submission.ACCEPTED:
        artifacts = Artifact.objects.filter(
            camera_ready__submission=submission, camera_ready__active=True)
        for artifact in artifacts:
            if artifact.descriptor.mandatory and not artifact.attachment.file:
                warnings.append(wc(
                    f'{artifact.attachment.name} missing', url_camera_ready,
                    link_label='upload...'))

    return warnings


def get_proc_type(submission):
    """Get proceedings type, if valuable for the submission, i.e. it is in
    `ACCEPT`, `PRINT` or `PUBLISH` state.

    :param submission: `Submission` instance
    :return: `ProcType` instance, or `None`
    """
    status = submission.status
    rev_stage = submission.reviewstage_set.first()
    decision_type = rev_stage.decision.decision_type if rev_stage else None
    if decision_type and status in {Submission.ACCEPTED, Submission.IN_PRINT,
                                    Submission.PUBLISHED}:
        return decision_type.description
    return None


def get_volume(submission):
    """Get volume, if valuable for the submission, i.e. it is in
    `ACCEPT`, `PRINT` or `PUBLISH` state, and proceedings type is known.

    :param submission: `Submission` instance
    :return: `Volume` instance, or `None`
    """
    status = submission.status
    decision = submission.old_decision.first()
    if (decision and decision.proc_type and
            status in {Submission.ACCEPTED, Submission.IN_PRINT,
                       Submission.PUBLISHED}):
        return decision.volume
    return None
