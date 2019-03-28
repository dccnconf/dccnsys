# Generated by Django 2.1.7 on 2019-03-28 08:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('conferences', '0002_auto_20190328_1058'),
    ]

    operations = [
        migrations.AddField(
            model_name='conference',
            name='chairs',
            field=models.ManyToManyField(related_name='chaired_conferences', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='conference',
            name='creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_conferences', to=settings.AUTH_USER_MODEL),
        ),
    ]
