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
            submission=camera.submission_id,
            access=access,
            code=descriptor.code,
            name=descriptor.name,
            label=descriptor.description,
        )
        instance.attachment = attachment
        instance.save()


# noinspection PyUnusedLocal
@receiver(post_save, sender=ArtifactDescriptor)
def create_artifacts_on_artifact_descriptor_create(
        sender, instance, created, **kwargs):
    assert isinstance(instance, ArtifactDescriptor)
    if created:
        pt = instance.proc_type_id
        cameras = CameraReady.objects.filter(proc_type=instance.proc_type_id)
        for camera in cameras:
            art, created = camera.artifact_set.get_or_create(
                camera_ready=camera, descriptor=instance)


# noinspection PyUnusedLocal
@receiver(post_save, sender=ArtifactDescriptor)
def update_attachment_on_artifact_descriptor_update(
        sender, instance, created, **kwargs):
    assert isinstance(instance, ArtifactDescriptor)
    if not created:
        artifacts = Artifact.objects.filter(descriptor=instance)
        na = Attachment.READWRITE if instance.editable else Attachment.READONLY
        updated = []
        for art in artifacts:
            camera = art.camera_ready
            access = Attachment.INACTIVE
            if camera and art.camera_ready.active:
                access = na
            attachment = art.attachment
            if attachment.access != access:
                attachment.access = access
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
