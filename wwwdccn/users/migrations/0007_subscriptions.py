# Generated by Django 2.1.7 on 2019-03-27 14:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20190326_2013'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscriptions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trans_email', models.BooleanField(default=False, verbose_name='I agree to receive transactional emails from DCCN Registration System corresponding to actions related to me (e.g., submission status update, adding me as a co-author, invitations for review, etc.)')),
                ('info_email', models.BooleanField(default=False, verbose_name='I agree to receive informational emails related to DCCN 2019 and future DCCN events')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
