# Generated by Django 2.2.4 on 2019-10-02 17:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
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
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='submissions.Submission'),
        ),
    ]
