# Generated by Django 2.2.4 on 2019-10-02 11:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0014_artifactdescriptor_mandatory'),
        ('submissions', '0008_add_fields_to_attachment'),
        ('proceedings', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='VolumeAssignment',
            new_name='CameraReady',
        ),
    ]
