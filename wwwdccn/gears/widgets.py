from django.forms import FileInput, CheckboxSelectMultiple, Select


class CustomFileInput(FileInput):
    template_name = 'gears/widgets/file_input.html'
    accept = ''
    show_file_name = True


class CustomCheckboxSelectMultiple(CheckboxSelectMultiple):
    template_name = 'gears/widgets/checkbox_multiple_select.html'
    hide_label = False
    hide_apply_btn = False

    class Media:
        js = ('gears/js/checkbox_multiple_select.js',)

    def __init__(self, *args, **kwargs):
        self.hide_label = kwargs.pop('hide_label', False)
        self.hide_apply_btn = kwargs.pop('hide_apply_btn', False)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'hide_label': self.hide_label,
            'hide_apply_btn': self.hide_apply_btn,
        })
        return context


class DropdownSelectSubmit(Select):
    template_name = 'gears/widgets/dropdown_select_submit.html'
    empty_label = 'Not selected'
    label_class = ''
    empty_label_class = 'text-warning'
    nonempty_label_class = 'text-success'

    class Media:
        js = ('gears/js/dropdown_select_submit.js',)

    def __init__(self, *args, **kwargs):
        self.empty_label = kwargs.pop('empty_label', 'Not selected')
        self.label_class = kwargs.pop('label_class', '')
        self.empty_label_class = kwargs.pop('empty_label_class', 'text-warning')
        self.nonempty_label_class = kwargs.pop(
            'nonempty_label_class', 'text-success')
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context['widget']
        widget['label_class'] = self.label_class
        widget['empty_label_class'] = self.empty_label_class
        widget['nonempty_label_class'] = self.nonempty_label_class
        widget['label'] = self.empty_label
        widget['empty'] = True

        # context inherits optgroups, which stores data about
        # options and selected value. Here we find it and put to the context:
        for (_, options, _) in context['widget']['optgroups']:
            found = False
            for option in options:
                if option['selected'] and option['value']:
                    widget['label'] = option['label']
                    widget['empty'] = False
                    found = True
                    break
            if found:
                break
        return context
