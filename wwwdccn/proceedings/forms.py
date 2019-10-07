from django.forms import ModelForm

from gears.widgets import DropdownSelectSubmit
from proceedings.models import CameraReady


EMPTY_VOLUME_LABEL = '(no volume)'


class UpdateVolumeForm(ModelForm):

    class Meta:
        model = CameraReady
        fields = ['volume']
        widgets = {
            'volume': DropdownSelectSubmit(
                empty_label=EMPTY_VOLUME_LABEL,
                label_class='font-weight-normal dccn-text-small',
                empty_label_class='text-warning-18',
                nonempty_label_class='text-success-18',
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['volume'].queryset = self.instance.proc_type.volumes.all()
        self.fields['volume'].empty_label = EMPTY_VOLUME_LABEL
