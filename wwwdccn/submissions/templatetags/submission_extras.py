from django import template
from django.utils import timezone

from conferences.models import ArtifactDescriptor
from submissions import utilities
from submissions.helpers import get_affiliations_of, get_countries_of

register = template.Library()


@register.filter('status_class')
def status_class(submission):
    try:
        status = submission.status
        warnings = submission.warnings()
    except AttributeError:
        status = submission['status']
        warnings = submission['warnings']

    if status == 'SUBMIT':
        return 'text-success' if not warnings else 'text-warning'
    elif status in {'REVIEW', 'PRINT', 'PUBLISH'}:
        return 'text-info'
    elif status == 'ACCEPT':
        return 'text-success'
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
