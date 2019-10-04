# Generated by Django 2.2.4 on 2019-10-02 17:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('proceedings', '0004_create_artifacts_for_existing_attachments'),
        ('submissions', '0008_add_access_and_label_fields_to_attachment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='attachment',
            options={'ordering': ['id']},
        ),
        migrations.RemoveField(
            model_name='attachment',
            name='descriptor',
        ),
    ]
