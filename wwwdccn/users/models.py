import io
from datetime import date

import pyavagen
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django_countries.fields import CountryField

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

    has_finished_registration = models.BooleanField(
        default=False
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


def get_avatar_full_path(instance, filename):
    ext = filename.split('.')[-1]
    path = f'{settings.MEDIA_PUBLIC_ROOT}/avatars'
    name = f'{instance.pk}_{instance.avatar_version:04d}'
    return f'{path}/{name}.{ext}'


class Profile(models.Model):
    ROLES = (
        (None, _('Select your role')),
        ('Student', _('Student')),
        ('PhD Student', _('PhD Student')),
        ('Assistant', _('Assistant')),
        ('Researcher', _('Researcher')),
        ('Assistant Professor', _('Assistant Professor')),
        ('Associate Professor', _('Associate Professor')),
        ('Professor', _('Professor')),
        ('Head of Department', _('Head of Department')),
        ('Head of Faculty', _('Head of Faculty')),
        ('Head of Laboratory', _('Head of Laboratory')),
        ('Vice Rector', _('Vice Rector')),
        ('Rector', _('Rector')),
        ('Software Developer', _('Software Developer')),
        ('Engineer', _('Engineer')),
        ('Technician', _('Technician')),
        ('Economist', _('Economist')),
        ('Lawyer', _('Lawyer')),
        ('Instructor', _('Instructor')),
        ('Consultant', _('Consultant')),
        ('Manager', _('Manager')),
        ('Administrator', _('Administrator')),
        ('Analyst', _('Analyst')),
        ('Journalist', _('Journalist')),
        ('Writer', _('Writer')),
        ('Editor', _('Editor')),
        ('Librarian', _('Librarian')),
        ('Vice Director', _('Vice Director')),
        ('Chief Executive Officer', _('Chief Executive Officer')),
        ('Retired', _('Retired')),
        ('Other', _('Other')),
    )

    DEGREE = (
        (None, _('Select your degree')),
        ('Undergraduate', _('Undergraduate')),
        ('Bachelor', _('Bachelor')),
        ('Master', _('Master')),
        ('PhD', _('PhD')),
        ('Candidate of Sciences', _('Candidate of Sciences')),
        ('Doctor of Sciences', _('Doctor of Sciences')),
    )

    LANGUAGES = (
        ('ENG', _('English')),
        ('RUS', _('Russian')),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    first_name = models.CharField(
        max_length=100, verbose_name=_("First Name in English")
    )
    last_name = models.CharField(
        max_length=100, verbose_name=_("Last Name in English")
    )
    first_name_rus = models.CharField(
        max_length=100, default="", verbose_name=_("First Name in Russian",),
        blank=True,
    )
    middle_name_rus = models.CharField(
        max_length=100, default="", verbose_name=_("Middle Name in Russian"),
        blank = True,
    )
    last_name_rus = models.CharField(
        max_length=100, default="", verbose_name=_("Last Name in Russian"),
        blank=True,
    )
    country = CountryField(null=True, verbose_name=_("Country"))
    city = models.CharField(max_length=100, verbose_name=_("City in English"))
    birthday = models.DateField(verbose_name=_("Birthday"), null=True)
    affiliation = models.CharField(
        max_length=100, verbose_name=_("Name of your organization in English"),
    )
    role = models.CharField(
        choices=ROLES, max_length=30, null=True,
        verbose_name=_('Primary role in organization')
    )
    degree = models.CharField(
        choices=DEGREE, max_length=30, null=True,
        verbose_name=_('Degree')
    )
    ieee_member = models.BooleanField(
        verbose_name=_('I am an IEEE Member'), default=False
    )

    preferred_language = models.CharField(
        choices=LANGUAGES, max_length=3, default='ENG'
    )

    avatar = models.ImageField(upload_to=get_avatar_full_path, blank=True)
    avatar_version = models.IntegerField(default=0, blank=True, editable=False)

    @property
    def email(self):
        return self.user.email

    def get_short_name(self):
        return self.first_name

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_full_name_rus(self):
        return ' '.join(
            (self.first_name_rus, self.middle_name_rus, self.last_name_rus)
        )

    def has_name_rus(self):
        return bool(self.get_full_name_rus().strip())

    def age(self):
        today = date.today()
        born = self.birthday
        rest = 1 if (today.month, today.day) < (born.month, born.day) else 0
        return today.year - born.year - rest

    def __str__(self):
        return self.get_full_name()


def generate_avatar(profile):
    img_io = io.BytesIO()
    avatar = pyavagen.Avatar(
        pyavagen.CHAR_SQUARE_AVATAR,
        size=500,
        string=profile.get_full_name(),
        blur_radius=100
    )
    avatar.generate().save(img_io, format='PNG', quality=100)
    img_content = ContentFile(img_io.getvalue(), f'{profile.pk}.png')
    return img_content


def change_avatar(profile, image_file):
    if profile.avatar:
        profile.avatar.delete()
    profile.avatar_version += 1
    profile.avatar = image_file
    profile.save()
    return profile


class Subscriptions(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    trans_email = models.BooleanField(
        default=False,
        verbose_name=_('I agree to receive transactional emails from DCCN '
                       'Registration System corresponding to actions related '
                       'to me (e.g., submission status update, adding me as '
                       'a co-author, invitations for review, etc.)')
    )

    info_email = models.BooleanField(
        default=False,
        verbose_name=_('I agree to receive informational emails related to '
                       'DCCN 2019 and future DCCN events')
    )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Subscriptions.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
    instance.subscriptions.save()
