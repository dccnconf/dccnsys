from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from conferences.utilities import validate_chair_access
from proceedings.forms import UpdateVolumeForm
from proceedings.models import CameraReady


@require_POST
def update_volume(request, camera_id):
    camera = get_object_or_404(CameraReady, id=camera_id)
    validate_chair_access(request.user, camera.submission.conference)
    form = UpdateVolumeForm(request.POST, instance=camera)
    if form.is_valid():
        form.save()
        return JsonResponse(status=200, data={})
    return JsonResponse(status=500, data={})
