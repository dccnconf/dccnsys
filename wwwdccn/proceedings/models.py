from django.db.models import Model, ForeignKey, CASCADE, SET_NULL, BooleanField
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from conferences.models import ProceedingType, ProceedingVolume, \
    ArtifactDescriptor
from submissions.models import Submission, Attachment


class CameraReady(Model):
    submission = ForeignKey(
        Submission, on_delete=CASCADE, null=True, blank=True)

    proc_type = ForeignKey(
        ProceedingType, on_delete=SET_NULL, null=True, blank=True)

    volume = ForeignKey(
        ProceedingVolume, on_delete=SET_NULL, null=True, blank=True,
        default=None)

    active = BooleanField(default=False)

    class Meta:
        ordering = ['id']
        unique_together = ['submission', 'proc_type']

    def __str__(self):
        is_active = " [INACTIVE]" if not self.active else ""
        return f'{self.id}: camera-ready of submission ({self.submission_id})' \
               f' in proceedings ({self.proc_type_id}),' \
               f' volume ({self.volume_id}){is_active}'


@receiver(post_save, sender=Submission)
def create_cameras_on_submission_accept(**kwargs):
    """When a submission is accepted, create cameras for allowed proceeding
    types and mark them active. Cameras for all other proceeding types
    (those were possible due to submission type) mark as inactive.

    In all other cases except submission being printed or published,
    mark all existing cameras as inactive.
    """
    submission = kwargs['instance']
    stage = submission.reviewstage_set.first()
    decision_type = stage.decision.decision_type if stage else None
    if decision_type is not None and submission.status == Submission.ACCEPTED:
        allowed_proc_types = list(decision_type.allowed_proceedings.all())
        all_proc_types = list(submission.stype.possible_proceedings.all())
        for proc_type in all_proc_types:
            camera, _ = CameraReady.objects.get_or_create(
                submission=submission, proc_type=proc_type)
            camera.active = proc_type in allowed_proc_types
            camera.save()
    elif submission not in {Submission.IN_PRINT, Submission.PUBLISHED}:
        for camera in submission.cameraready_set.all():
            camera.active = False
            camera.save()


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


# noinspection PyUnusedLocal
@receiver(post_save, sender=Artifact)
def create_attachment_on_new_artifact(sender, instance, created, **kwargs):
    assert isinstance(instance, Artifact)
    if created:
        camera = instance.camera_ready
        access = Attachment.INACTIVE if not camera.active else (
            Attachment.READWRITE if instance.descriptor.editable else
            Attachment.READONLY
        )
        descriptor = instance.descriptor
        attachment = Attachment.objects.create(
            submission=camera.submission,
            access=access,
            code=descriptor.code,
            name=descriptor.name,
            label=descriptor.name,
        )
        instance.attachment = attachment
        instance.save()


# noinspection PyUnusedLocal
@receiver(post_save, sender=CameraReady)
def create_artifacts_on_new_camera(sender, instance, created, **kwargs):
    assert isinstance(instance, CameraReady)
    if created:
        descriptors = ArtifactDescriptor.objects.filter(
            proc_type=instance.proc_type_id)
        for descriptor in descriptors:
            Artifact.objects.get_or_create(
                camera_ready=instance, descriptor=descriptor)


# noinspection PyUnusedLocal
@receiver(post_save, sender=ArtifactDescriptor)
def create_artifacts_on_artifact_descriptor_create(
        sender, instance, created, **kwargs):
    assert isinstance(instance, ArtifactDescriptor)
    if created:
        pt = instance.proc_type_id
        cameras = CameraReady.objects.filter(proc_type=instance.proc_type_id)
        for camera in cameras:
            camera.artifact_set.get_or_create(
                camera_ready=camera, descriptor=instance)


def _update_attachment_access(attachment, descriptor, camera):
    access = Attachment.INACTIVE
    if camera and camera.active:
        access = Attachment.READWRITE if descriptor.editable else \
            Attachment.READONLY
    if attachment.access != access:
        attachment.access = access
        return True
    return False


# noinspection PyUnusedLocal
@receiver(post_save, sender=ArtifactDescriptor)
def update_attachment_on_descriptor_update(sender, instance, created, **kwargs):
    assert isinstance(instance, ArtifactDescriptor)
    if not created:
        artifacts = Artifact.objects.filter(descriptor=instance)
        na = Attachment.READWRITE if instance.editable else Attachment.READONLY
        updated = []
        for art in artifacts:
            attachment, camera = art.attachment, art.camera_ready
            if _update_attachment_access(
                    attachment=attachment, descriptor=instance, camera=camera):
                updated.append(attachment)
        if updated:
            Attachment.objects.bulk_update(updated, ['access'])


# noinspection PyUnusedLocal
@receiver(post_save, sender=CameraReady)
def update_attachment_on_camera_update(sender, instance, created, **kwargs):
    assert isinstance(instance, CameraReady)
    if not created:
        updated = []
        for art in instance.artifact_set.all():
            attachment, descriptor = art.attachment, art.descriptor
            if _update_attachment_access(
                    attachment=attachment, descriptor=descriptor,
                    camera=instance):
                updated.append(attachment)
        if updated:
            Attachment.objects.bulk_update(updated, ['access'])


# noinspection PyUnusedLocal
@receiver(pre_delete, sender=ArtifactDescriptor)
def delete_artifacts_on_artifact_descriptor_delete(sender, instance, **kwargs):
    assert isinstance(instance, ArtifactDescriptor)
    updated = []
    for att in Attachment.objects.filter(artifact__descriptor=instance):
        if att.access != Attachment.INACTIVE:
            att.access = Attachment.INACTIVE
            updated.append(att)
    if updated:
        Attachment.objects.bulk_update(updated, ['access'])
    for art in Artifact.objects.filter(descriptor=instance):
        art.delete()
