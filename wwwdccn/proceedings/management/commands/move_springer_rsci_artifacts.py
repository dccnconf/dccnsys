from django.core.management.base import BaseCommand, CommandError

from conferences.models import ProceedingType, ArtifactDescriptor
from proceedings.models import Artifact
from submissions.models import Attachment


class Command(BaseCommand):
    help = 'Move "RSCI Final PDF" artifacts from Springer proceedings to ' \
           'RSCI proceedings.'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--fake', action='store_true',
                            help='Do not write changes to the DB')
        # parser.add_argument('-v', '--verbose', action='store_true',
        #                     help='Additional details output to screen')

    def handle(self, *args, **kwargs):
        fake = kwargs['fake']
        verbosity = kwargs['verbosity']

        if fake:
            self.stdout.write(self.style.NOTICE('* Started in fake mode'))

        #
        # Loading proceedings types and descriptors:
        #
        rsci_proc_type = ProceedingType.objects.filter(
            name__icontains='rsci').first()
        springer_proc_type = ProceedingType.objects.filter(
            name__icontains='springer').first()

        self._check_found(
            rsci_proc_type, fields=['name'], verbosity=verbosity,
            name='RSCI proceedings')
        self._check_found(
            springer_proc_type, fields=['name'], verbosity=verbosity,
            name='Springer proceedings',)

        rsci_descriptor = ArtifactDescriptor.objects.filter(
            proc_type=rsci_proc_type).first()
        springer_descriptor = ArtifactDescriptor.objects.filter(
            proc_type=springer_proc_type,
            name__icontains='rsci').first()

        self._check_found(
            rsci_descriptor, fields=['name', 'proc_type_id'],
            verbosity=verbosity, name='RSCI artifact descriptor')
        self._check_found(
            springer_descriptor, fields=['name', 'proc_type_id'],
            verbosity=verbosity,
            name='Springer artifact descriptor for RSCI proceedings')

        #
        # Looping through artifacts we need to move:
        #
        updated_artifacts = []
        deleted_artifacts = []
        artifacts = Artifact.objects.filter(descriptor=springer_descriptor)
        if verbosity > 1:
            self.stdout.write(self.style.SUCCESS(
                f'* Found {artifacts.count()} artifacts to move'))

        for art in artifacts:
            curr_camera, attachment = art.camera_ready, art.attachment
            sub = art.attachment.submission if art.attachment else None
            if sub is None:
                self.stdout.write(self.style.WARNING(
                    f'! artifact {art.id} submission is unknown'))

            _ss = f'submission #{sub.id}'
            if curr_camera and curr_camera.proc_type != springer_proc_type:
                self.stdout.write(self.style.WARNING(
                    f'! current camera-ready of artifact {art.id} proceedings'
                    f'type is not Springer ({curr_camera.proc_type_id} != '
                    f'{springer_proc_type.id}); skipping artifact'))
                continue

            if fake:
                rsci_camera = sub.cameraready_set.filter(
                    proc_type_id=rsci_proc_type).first()
                created = rsci_camera is None
                rsci_camera_id = rsci_camera.id if not created else \
                    '<unknown ID in fake mode>'
            else:
                rsci_camera, created = sub.cameraready_set.get_or_create(
                    proc_type_id=rsci_proc_type.id, submission=sub)
                rsci_camera_id = rsci_camera.id
            if created:
                if not fake:
                    rsci_camera.ready = False
                    rsci_camera.save()
                    attachment.access = Attachment.INACTIVE
                    attachment.save()
                self.stdout.write(self.style.WARNING(
                    f"! artifact {art.id} was missing RSCI camera-ready "
                    f"(possibly this submission {sub.id} was rejected); "
                    f"created a new camera-ready {rsci_camera_id} in "
                    f"INACTIVE state and set attachment {attachment.id} "
                    f'access to "No-Access"'))

            # Before binding current artifact to RSCI camera-ready, we also
            # need to check whether this camera-ready was previously filled
            # with another artifact (e.g., chair changed his/her mind and
            # moved submission to Springer).
            # - Check which artifact had a non-empty attachment,
            #   and leave that one while delete another.
            #
            # - If both are empty, leave the new artifact.
            #
            # - If both are non-empty, leave both.
            if rsci_camera:
                old_rsci_artifacts = rsci_camera.artifact_set.filter(
                    descriptor=rsci_descriptor)
                n_old = old_rsci_artifacts.count()
                if n_old > 0:
                    _empty = old_rsci_artifacts.filter(
                        attachment__file='')
                    deleted_artifacts.extend(list(_empty))
                    n_empty = _empty.count()
                    if n_empty > 0:
                        self.stdout.write(self.style.WARNING(
                            f'! Found {n_empty} old empty artifacts on RSCI '
                            f'camera-ready {rsci_camera_id} of submission '
                            f'{sub.id}, marking to remove'))
                    if n_old > n_empty and not attachment.file:
                        deleted_artifacts.append(art)
                        self.stdout.write(self.style.WARNING(
                            f'! RSCI camera-ready {rsci_camera_id} of '
                            f'submission {sub.id} has {n_old - n_empty} '
                            f'non-empty artifact(s) with RSCI descriptor '
                            f'{rsci_descriptor.id}. Since current artifact '
                            f'{art.id} is empty, delete it.'))
                        continue

                # If everything is OK, switching camera-ready and descriptor
                # for the current artifact:
                art.descriptor = rsci_descriptor
                art.camera_ready = rsci_camera
                updated_artifacts.append(art)

        # Running update:
        if verbosity > 1:
            self.stdout.write(self.style.SUCCESS(
                f'* Updating {len(updated_artifacts)} artifacts'))
        if not fake and updated_artifacts:
            Artifact.objects.bulk_update(
                updated_artifacts, ['descriptor', 'camera_ready'])

        if verbosity > 1:
            self.stdout.write(self.style.SUCCESS(
                f'* Deleting {len(deleted_artifacts)} artifacts'))
        if not fake and deleted_artifacts:
            for art in deleted_artifacts:
                art.delete()

        #
        # If not faked, check that we actually moved artifacts (we
        # need to check fake since actual update :
        #
        num_arts = springer_descriptor.artifact_set.count()
        if not fake and num_arts > 0:
            self.stdout.write(self.style.WARNING(
                f'! Found {num_arts} on descriptor {springer_descriptor.id}'))

        #
        # Remove unused artifact descriptor (RSCI for Springer proceedings):
        #
        if not fake and num_arts == 0:
            springer_descriptor.delete()
            if verbosity > 1:
                self.stdout.write(self.style.SUCCESS(
                    f'* Removed Springer descriptor for RSCI proceedings'))

        self.stdout.write(self.style.SUCCESS('= Finished.'))

    def _check_found(self, var, name, fields=None, verbosity=1):
        if not var:
            self.stderr.write(self.style.ERROR(f'ERROR: {name} not found'))
            raise CommandError
        if verbosity > 1:
            parts = [(field, getattr(var, field)) for field in fields]
            suffix = ', '.join([f'{k}="{v}"' for (k, v) in parts])
            if suffix:
                suffix = ', ' + suffix
            self.stdout.write(self.style.SUCCESS(
                f'* Found {name}: ID={var.id}{suffix}'))
