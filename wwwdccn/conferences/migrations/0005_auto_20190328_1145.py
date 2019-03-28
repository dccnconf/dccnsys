# Generated by Django 2.1.7 on 2019-03-28 08:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0004_remove_conference_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reviewstage',
            name='conference',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review_stage', to='conferences.Conference'),
        ),
        migrations.AlterField(
            model_name='submissionstage',
            name='conference',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='submission_stage', to='conferences.Conference'),
        ),
    ]
