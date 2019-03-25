from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import ugettext_lazy as _
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name=_('Email address'), unique=True)

    date_joined = models.DateTimeField(
        verbose_name=_('Date joined'),
        auto_now_add=True
    )

    is_active = models.BooleanField(
        verbose_name=_('Active'),
        default=True
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    # TODO: uncomment this later:
    # def get_absolute_url(self):
    #     return reverse('user-detail', kwargs={'pk': self.id})

    def __str__(self):
        return f'{self.pk}: {self.email}'
