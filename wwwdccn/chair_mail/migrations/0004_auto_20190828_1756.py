# Generated by Django 2.2.4 on 2019-08-28 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chair_mail', '0003_auto_20190826_1257'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemnotification',
            name='name',
            field=models.CharField(choices=[('assign_status_review', 'Assign status REVIEW to the paper'), ('assign_status_submit', 'Assign status SUBMIT to the paper'), ('assign_status_accept', 'Assign status ACCEPT to the paper'), ('assign_status_reject', 'Assign status REJECT to the paper')], max_length=64),
        ),
    ]
