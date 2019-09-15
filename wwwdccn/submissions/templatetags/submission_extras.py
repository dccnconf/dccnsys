from django import template

from conferences.models import ArtifactDescriptor
from submissions import utilities
from submissions.helpers import get_affiliations_of, get_countries_of
from submissions.utilities import list_warnings, get_proc_type, get_volume

register = template.Library()


@register.filter('status_class')
def status_class(submission):
    status = submission.status
    if status == 'SUBMIT':
        return 'text-success-4'
    elif status in {'REVIEW', 'PRINT', 'PUBLISH'}:
        return 'text-info'
    elif status == 'ACCEPT':
        return 'text-success-12'
    elif status == 'REJECT':
        return 'text-danger'
    return ''


@register.filter
def affiliations(submission):
    return get_affiliations_of(submission)


@register.filter
def countries(submission):
    return get_countries_of(submission)


@register.filter
def camera_editable(submission):
    return utilities.camera_editable(submission)


@register.filter
def artifacts_of(submission):
    return [artifact for artifact in submission.artifacts.all()
            if artifact.is_active]


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
def warnings_of(submission, role='author'):
    """List all warnings for the submission.

    :param submission:
    :param role: 'author' or 'chair'
    :return:
    """
    from submissions.models import Submission
    warnings = list_warnings(submission)
    # if submission.status == Submission.ACCEPTED:
    #     for artifact in artifacts_of(submission):
    #         if artifact.descriptor.mandatory and not artifact.file:
    #             warnings.append(f'{artifact.name} missing')
    return [w for w in warnings if role in w.visible_by]


@register.filter
def count_warnings(submission, role='author'):
    return len(warnings_of(submission, role))


@register.filter
def proc_type_of(submission):
    return get_proc_type(submission)


@register.filter
def volume_of(submission):
    return get_volume(submission)
