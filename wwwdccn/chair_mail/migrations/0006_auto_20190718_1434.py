# Generated by Django 2.1.10 on 2019-07-18 11:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chair_mail', '0005_emailgeneralsettings_logo_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailmessage',
            name='sent_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_email_messages', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='emailmessageinst',
            name='sent_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_email_instances', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='emailmessage',
            name='users_to',
            field=models.ManyToManyField(related_name='email_messages', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='emailmessageinst',
            name='user_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_instances', to=settings.AUTH_USER_MODEL),
        ),
    ]