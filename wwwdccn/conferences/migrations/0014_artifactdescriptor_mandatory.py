# Generated by Django 2.2.4 on 2019-08-29 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0013_auto_20190829_2142'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifactdescriptor',
            name='mandatory',
            field=models.BooleanField(default=True, verbose_name='Artifact is mandatory'),
        ),
    ]
