from django.forms import FileInput, CheckboxSelectMultiple


class CustomFileInput(FileInput):
    template_name = 'gears/widgets/file_input.html'
    accept = ''
    show_file_name = True


class CustomCheckboxSelectMultiple(CheckboxSelectMultiple):
    template_name = 'gears/widgets/checkbox_multiple_select.html'

    class Media:
        js = ('gears/js/checkbox_multiple_select.js',)
