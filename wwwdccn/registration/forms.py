from django.forms import ModelForm, DateInput, TextInput

from users.models import Profile


class PersonalForm(ModelForm):
    class Meta:
        model = Profile
        fields = (
            'first_name', 'last_name', 'first_name_rus', 'middle_name_rus',
            'last_name_rus', 'country', 'city', 'birthday', 'preferred_language'
        )
        widgets = {
            'birthday': TextInput(attrs={'class': 'datepicker'})
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


class ProfessionalForm(ModelForm):
    class Meta:
        model = Profile
        fields = ('affiliation', 'degree', 'role', 'ieee_member',
                  'agree_to_receive_emails')
