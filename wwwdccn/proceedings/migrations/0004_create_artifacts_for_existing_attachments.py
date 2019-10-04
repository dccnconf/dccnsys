from django.db import migrations, models


# noinspection PyPep8Naming,PyUnusedLocal
def create_artifacts(apps, schema_editor):
    Artifact = apps.get_model('proceedings', 'Artifact')
    CameraReady = apps.get_model('proceedings', 'CameraReady')
    Attachment = apps.get_model('submissions', 'Attachment')

    artifacts = []
    updated_attachments = []
    for at in Attachment.objects.all():
        descriptor = at.descriptor
        camera_ready = CameraReady.objects.filter(
            submission=at.submission_id, proc_type=descriptor.proc_type_id
        ).first()
        artifacts.append(Artifact(
            camera_ready=camera_ready,
            attachment=at,
            descriptor=descriptor,
        ))
        # Here we also set attachment labels and access modes:
        if camera_ready and camera_ready.active:
            status = at.submission.status
            if status == 'ACCEPT':
                at.access = 'RW'
            elif status in {'PRINT', 'PUBLISH'}:
                at.access = 'RO'
            else:
                at.access = 'NO'
        else:
            at.access = 'NO'
        if descriptor:
            at.name = descriptor.name
            at.label = descriptor.description
            at.code = descriptor.code
        updated_attachments.append(at)

    Artifact.objects.bulk_create(artifacts)
    Attachment.objects.bulk_update(
        updated_attachments, ['access', 'label', 'name', 'code'])


class Migration(migrations.Migration):
    dependencies = [
        ('proceedings', '0003_artifact'),
        ('submissions', '0008_add_access_and_label_fields_to_attachment'),
        ('review', '0011_create_new_decisions_and_types')
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='code',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='attachment',
            name='name',
            field=models.CharField(blank=True, default='', max_length=256),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='submission',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE,
                                    related_name='attachments',
                                    to='submissions.Submission'),
        ),
        migrations.RunPython(create_artifacts),
    ]
