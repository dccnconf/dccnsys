from django.db.models import Model, ForeignKey, CASCADE, SET_NULL, BooleanField

from conferences.models import ProceedingType, ProceedingVolume, \
    ArtifactDescriptor
from submissions.models import Submission, Attachment


class CameraReady(Model):
    submission = ForeignKey(
        Submission, on_delete=CASCADE, null=True, blank=True)

    proc_type = ForeignKey(
        ProceedingType, on_delete=SET_NULL, null=True, blank=True)

    volume = ForeignKey(
        ProceedingVolume, on_delete=SET_NULL, null=True, blank=True)

    active = BooleanField(default=False)

    def __str__(self):
        is_active = " [INACTIVE]" if not self.active else ""
        return f'{self.id}: camera-ready of submission ({self.submission_id})' \
               f' in proceedings ({self.proc_type_id}),' \
               f' volume ({self.volume_id}){is_active}'


class Artifact(Model):
    camera_ready = ForeignKey(CameraReady, on_delete=SET_NULL, null=True,
                              blank=True)

    attachment = ForeignKey(Attachment, on_delete=CASCADE, null=True,
                            blank=True)

    descriptor = ForeignKey(ArtifactDescriptor, on_delete=SET_NULL, null=True,
                            blank=True)

    def __str__(self):
        return f"{self.id}: artifact for camera ({self.camera_ready_id}), " \
               f"attachment ({self.attachment_id}), descriptor " \
               f"({self.descriptor_id})"
