from django.db import models

from conferences.models import Conference
from users.models import User


class HtmlEmailTemplate(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    body = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("name", "conference"),)


class TextEmailTemplate(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    body = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("name", "conference"),)


class EmailMessage(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    html = models.TextField()
    text = models.TextField()
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("name", "conference"),)


class EmailUserList(models.Model):
    name = models.CharField(max_length=1024, blank=False)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    users = models.ManyToManyField(User)

    class Meta:
        unique_together = (("name", "conference"),)


class EmailGeneralSettings(models.Model):
    footer_html = models.TextField()
    footer_text = models.TextField()
    sign_footer_html = models.TextField()
    sign_footer_text = models.TextField()
