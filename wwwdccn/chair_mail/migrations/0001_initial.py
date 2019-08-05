# Generated by Django 2.1.10 on 2019-08-01 14:24

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('conferences', '0009_conference_contact_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailFrame',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_html', models.TextField()),
                ('text_plain', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='conferences.Conference')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EmailMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.TextField(max_length=1024)),
                ('text_plain', models.TextField()),
                ('text_html', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('sent', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='EmailSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conference', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='email_settings', to='conferences.Conference')),
                ('frame', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='chair_mail.EmailFrame')),
            ],
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=1024)),
                ('body', models.TextField()),
                ('msg_type', models.CharField(blank=True, choices=[(None, 'Select message type'), ('user', 'Message for user'), ('submission', 'Message for submission authors')], max_length=128)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_templates', to='conferences.Conference')),
            ],
        ),
        migrations.CreateModel(
            name='GroupEmailMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('sent', models.BooleanField(default=False)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_group_emails', to='conferences.Conference')),
                ('sent_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_group_emails', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_emails', to='chair_mail.EmailTemplate')),
                ('users_to', models.ManyToManyField(related_name='group_emails', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='group_message',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='chair_mail.GroupEmailMessage'),
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='sent_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_emails', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='user_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='emails', to=settings.AUTH_USER_MODEL),
        ),
    ]
