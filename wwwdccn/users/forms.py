from django import forms
from django.forms import Form
from django.utils.translation import ugettext_lazy as _

from users.models import Profile, User


class PersonalForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            'first_name', 'last_name', 'first_name_rus', 'middle_name_rus',
            'last_name_rus', 'country', 'city', 'birthday', 'preferred_language'
        )
        widgets = {
            'birthday': forms.TextInput(attrs={'class': 'datepicker'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'first_name': 'e.g.: Ivan',
            'last_name': 'e.g.: Petrov',
            'first_name_rus': 'пр.: Иван',
            'middle_name_rus': 'пр.: Дмитриевич',
            'last_name_rus': 'пр.: Петров',
            'city': 'e.g.: Moscow',
            'birthday': 'e.g.: 1 January 1980',
        }
        for key, value in placeholders.items():
            self.fields[key].widget.attrs['placeholder'] = value


class ProfessionalForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('affiliation', 'degree', 'role', 'ieee_member')


class NotificationsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('agree_to_receive_emails',)


class PasswordProtectedForm(Form):
    password = forms.CharField(
        strip=False,
        label=_('Enter your password'),
        widget=forms.PasswordInput(attrs={'placeholder': _('Password')})
    )

    def clean_password(self):
        """Validate that the entered password is correct.
        """
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError(
                _("The password is incorrect"),
                code='password_incorrect'
            )
        return password


class DeleteUserForm(PasswordProtectedForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        self.user.delete()


class UpdateEmailForm(PasswordProtectedForm):
    email = forms.EmailField(label=_('Enter your new email'))

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        self.user.email = self.cleaned_data['email']
        self.user.save()
