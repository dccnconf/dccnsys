from django.db.models import Model, ForeignKey, CASCADE, SET_NULL, BooleanField

from conferences.models import ProceedingType, ProceedingVolume
from submissions.models import Submission


class VolumeAssignment(Model):
    submission = ForeignKey(
        Submission, on_delete=CASCADE, null=True, blank=True)

    proc_type = ForeignKey(
        ProceedingType, on_delete=SET_NULL, null=True, blank=True)

    volume = ForeignKey(
        ProceedingVolume, on_delete=SET_NULL, null=True, blank=True)

    active = BooleanField(default=False)
