# Generated by Django 2.1.7 on 2019-03-29 00:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Conference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=300, verbose_name='Full name of the conference')),
                ('short_name', models.CharField(max_length=30, verbose_name='Short name of the conference')),
                ('is_ieee', models.BooleanField(default=False, verbose_name='The conference is supported by IEEE')),
                ('country', django_countries.fields.CountryField(max_length=2, null=True, verbose_name='Country')),
                ('city', models.CharField(max_length=100, verbose_name='City')),
                ('start_date', models.DateField(null=True, verbose_name='Opens at')),
                ('close_date', models.DateField(null=True, verbose_name='Closes at')),
                ('logotype', models.ImageField(blank=True, null=True, upload_to='public//conferences/logo/', verbose_name='Conference logotype')),
                ('chairs', models.ManyToManyField(related_name='chaired_conferences', to=settings.AUTH_USER_MODEL)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_conferences', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProceedingType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Short name')),
                ('description', models.CharField(max_length=1000, verbose_name='Long description')),
                ('final_manuscript_deadline', models.DateField(null=True, verbose_name='Deadline for final manuscript submission')),
                ('min_num_pages', models.IntegerField(default=4, verbose_name='Minimum number of pages in submission')),
                ('max_num_pages', models.IntegerField(default=4, verbose_name='Maximum number of pages in submission')),
                ('final_latex_template', models.FileField(blank=True, null=True, upload_to='public//conferences/templates', verbose_name='LaTeX template for final manuscript')),
                ('_final_latex_template_version', models.IntegerField(default=1)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='conferences.Conference')),
            ],
        ),
        migrations.CreateModel(
            name='ReviewStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('end_date', models.DateField(null=True, verbose_name='End of review')),
                ('conference', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review_stage', to='conferences.Conference')),
            ],
        ),
        migrations.CreateModel(
            name='SubmissionStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('end_date', models.DateField(null=True, verbose_name='Deadline for submissions')),
                ('end_date_description', models.CharField(blank=True, max_length=100)),
                ('conference', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='submission_stage', to='conferences.Conference')),
            ],
        ),
        migrations.CreateModel(
            name='SubmissionType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Short name')),
                ('description', models.CharField(max_length=1000, verbose_name='Long description')),
                ('language', models.TextField(choices=[(None, 'Select submission language'), ('RU', 'Russian'), ('EN', 'English')], max_length=2)),
                ('latex_template', models.FileField(null=True, upload_to='public//conferences/templates', verbose_name='LaTeX template')),
                ('_latex_template_version', models.IntegerField(default=1)),
                ('num_reviews', models.IntegerField(default=2, verbose_name='Number of reviews per submission')),
                ('min_num_pages', models.IntegerField(default=4, verbose_name='Minimum number of pages in submission')),
                ('max_num_pages', models.IntegerField(default=4, verbose_name='Maximum number of pages in submission')),
                ('blind_review', models.BooleanField(default=False, verbose_name='Blind review')),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='conferences.Conference')),
                ('possible_proceedings', models.ManyToManyField(to='conferences.ProceedingType')),
            ],
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Topic name')),
                ('order', models.IntegerField(default=0)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='conferences.Conference')),
            ],
        ),
    ]
