from django import template

from conferences.models import ArtifactDescriptor
from submissions.helpers import get_affiliations_of, get_countries_of
from submissions.models import Submission
from submissions.utilities import list_warnings

register = template.Library()


@register.filter
def submission_status_color_class(submission):
    status = submission.status
    if status == Submission.SUBMITTED:
        return 'success-4'
    elif status == Submission.UNDER_REVIEW:
        return 'info'
    elif status == Submission.ACCEPTED:
        return 'success-12'
    elif status == Submission.REJECTED:
        return 'danger'
    elif status == Submission.IN_PRINT:
        return 'dark-5'
    return ''


@register.filter
def submission_affiliations(submission):
    return get_affiliations_of(submission)


@register.filter
def submission_countries(submission):
    return get_countries_of(submission)


@register.filter
def submission_attachments(submission):
    return [attachment for attachment in submission.attachments.all()
            if attachment.is_active]


@register.filter
def accepted_input(artifact):
    ft = artifact.descriptor.file_type
    if ft == ArtifactDescriptor.TYPE_PDF:
        return '.pdf'
    if ft == ArtifactDescriptor.TYPE_SCAN:
        return '.pdf,image/*'
    if ft == ArtifactDescriptor.TYPE_ZIP:
        return 'zip,application/octet-stream,application/zip,' \
               'application/x-zip,application/x-zip-compressed'
    return '*'


@register.filter
def file_icon_class(artifact):
    ft = artifact.descriptor.file_type
    if ft == ArtifactDescriptor.TYPE_PDF:
        return 'far fa-file-pdf'
    if ft == ArtifactDescriptor.TYPE_SCAN:
        return 'far fa-file-image'
    if ft == ArtifactDescriptor.TYPE_ZIP:
        return 'far fa-file-archive'
    return 'far file-alt'


@register.filter
def submission_warnings(submission, role='author'):
    """List all warnings for the submission.

    :param submission:
    :param role: 'author' or 'chair'
    :return:
    """
    warnings = list_warnings(submission)
    return [w for w in warnings if role in w.visible_by]


@register.filter
def count_submission_warnings(submission, role='author'):
    return len(submission_warnings(submission, role))
