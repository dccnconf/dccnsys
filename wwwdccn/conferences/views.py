from django.http import Http404, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET

from conferences.decorators import chair_required
from conferences.forms import ConferenceForm, SubmissionStageForm, \
    ReviewStageForm, ProceedingTypeForm, DeleteForm, SubmissionTypeForm, \
    TopicCreateForm, TopicsReorderForm, TopicEditForm, ProceedingVolumeForm, \
    ArtifactDescriptorForm
from conferences.models import Conference, ProceedingType, SubmissionType, \
    Topic, ProceedingVolume, ArtifactDescriptor
from submissions.models import Submission


def get_url_of(file_field, default=''):
    return file_field.url if file_field else default


# For get_country_display():
# noinspection PyUnresolvedReferences
@require_GET
def ajax_details(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return JsonResponse({
        'full_name': conference.full_name,
        'short_name': conference.short_name,
        'is_ieee': conference.is_ieee,
        'country': conference.get_country_display(),
        'city': conference.city,
        'start_date': conference.start_date,
        'close_date': conference.close_date,
        'logotype': get_url_of(conference.logotype),
        'description': conference.description,
        'site_url': conference.site_url,
        'submission_deadline': conference.submission_stage.end_date,
        'review_deadline': conference.review_stage.end_date,
        'topics': [
            topic.name for topic in conference.topic_set.order_by('order')
        ],
        'proceeding_volumes': [
            {
                'id': volume.pk,
                'name': volume.name,
                'description': volume.description,
                'deadline': volume.final_manuscript_deadline,
                'min_num_pages': volume.min_num_pages,
                'max_num_pages': volume.max_num_pages,
                'final_latex_template': get_url_of(volume.final_latex_template),
                'submission_types': [
                    {
                        'id': stype.pk,
                        'name': stype.name,
                    } for stype in volume.submissiontype_set.all()
                ]
            } for volume in conference.proceedingtype_set.all()
        ],
        'submission_types': [
            {
                'id': stype.pk,
                'name': stype.name,
                'description': stype.description,
                'language': stype.get_language_display(),
                'latex_template': get_url_of(stype.latex_template),
                'num_reviews': stype.num_reviews,
                'min_num_pages': stype.min_num_pages,
                'max_num_pages': stype.max_num_pages,
                'blind_review': stype.blind_review,
                'possible_proceedings': [
                    {
                        'id': proc.pk,
                        'name': proc.name,
                    } for proc in stype.possible_proceedings.all()
                ]
            } for stype in conference.submissiontype_set.all()
        ]
    })


@require_GET
def ajax_stype_details(request, pk):
    stype = get_object_or_404(SubmissionType, pk=pk)
    return JsonResponse({
        'id': stype.pk,
        'name': stype.name,
        'description': stype.description,
        'language': stype.get_language_display(),
        'latex_template': get_url_of(stype.latex_template),
        'num_reviews': stype.num_reviews,
        'min_num_pages': stype.min_num_pages,
        'max_num_pages': stype.max_num_pages,
        'blind_review': stype.blind_review,
        'possible_proceedings': [
            {
                'id': proc.pk,
                'name': proc.name,
            } for proc in stype.possible_proceedings.all()
        ]
    })


@login_required
def conferences_list(request):
    return render(request, 'conferences/list.html', {
        'conferences': Conference.objects.all(),
        'submissions': Submission.objects.filter(authors__user=request.user),
    })


@login_required
def conference_details(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return render(request, 'conferences/details.html', {
        'conference': conference,
    })


# TODO: implement and add admin_required decorator
@login_required
def conference_create(request):
    if request.method == 'POST':
        form = ConferenceForm(request.POST, request.FILES)
        if form.is_valid():
            conference = form.save()
            conference.creator = request.user
            conference.save()
            return redirect('conferences:details', pk=conference.pk)
    else:
        form = ConferenceForm()
    return render(request, 'conferences/create.html', {
        'form': form,
    })


@chair_required
def conference_edit(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    if request.method == 'POST':
        form = ConferenceForm(request.POST, request.FILES, instance=conference)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Conference #{pk} "{conference.short_name}" was updated'
            )
            return redirect('conferences:details', pk=pk)
    else:
        form = ConferenceForm(instance=conference)
    return render(request, 'conferences/form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Settings',
        'title': f'Edit conference #{pk}'
    })


@chair_required
def conference_submission_stage(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    stage = conference.submission_stage
    if request.method == 'POST':
        form = SubmissionStageForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Conference #{pk} submission stage settings were updated'
            )
            return redirect('conferences:details', pk=pk)
    else:
        form = SubmissionStageForm(instance=stage)
    return render(request, 'conferences/form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Submissions Stage',
        'title': f'Edit conference #{pk}',
    })


@chair_required
def conference_review_stage(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    stage = conference.review_stage
    if request.method == 'POST':
        form = ReviewStageForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Conference #{pk} review stage settings were updated'
            )
            return redirect('conferences:details', pk=pk)
    else:
        form = ReviewStageForm(instance=stage)
    return render(request, 'conferences/form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Reviews Stage',
        'title': f'Edit conference #{pk}',
    })


@chair_required
def proceedings_create(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    if request.method == 'POST':
        form = ProceedingTypeForm(request.POST, request.FILES)
        if form.is_valid():
            proceedings = form.save(commit=False)
            proceedings.conference = conference
            proceedings.save()
            messages.success(
                request,
                f'Proceedings were created'
            )
            return redirect('conferences:details', pk=pk)
    else:
        form = ProceedingTypeForm()
    return render(request, 'conferences/form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Define New Proceedings',
        'title': f'Conference #{pk}',
    })


@chair_required
def proceeding_type_details(request, pk, proc_pk):
    proceedings = get_object_or_404(ProceedingType, pk=proc_pk)
    conference = proceedings.conference

    if conference.pk != pk:
        raise Http404
    if request.method == 'POST':
        form = ProceedingTypeForm(request.POST, request.FILES,
                                  instance=proceedings)
        if form.is_valid():
            form.save()
            messages.success(request, f'{proceedings.name} updated')
            return redirect('conferences:proceedings-update',
                            pk=pk, proc_pk=proc_pk)
    else:
        form = ProceedingTypeForm(instance=proceedings)
    return render(request, 'conferences/proceeding_type_details.html', {
        'conference': conference,
        'form': form,
        'subtitle': f'Edit proceedings',
        'title': f'{conference.short_name} Conference',
        'proceeding_type': proceedings,
    })


@chair_required
@require_POST
def proceedings_delete(request, pk, proc_pk):
    proceedings = get_object_or_404(ProceedingType, pk=proc_pk)
    form = DeleteForm(proceedings, request.POST)
    form.save()
    messages.success(request, f'Deleted proceedings')
    return redirect('conferences:details', pk=pk)


@chair_required
def proceeding_volume_create(request, pk, proc_pk):
    ptype = get_object_or_404(ProceedingType, pk=proc_pk)
    if request.method == 'POST':
        form = ProceedingVolumeForm(request.POST)
        if form.is_valid():
            volume = form.save(commit=False)
            volume.type = ptype
            volume.save()
            messages.success(request, 'Volume was created')
            return redirect('conferences:proceedings-update',
                            pk=pk, proc_pk=proc_pk)
    else:
        form = ProceedingVolumeForm()
    return render(request, 'conferences/form.html', {
        'conference': ptype.conference,
        'form': form,
        'subtitle': 'New volume',
        'title': f'Conference #{ptype.conference_id}',
    })


@chair_required
def proceeding_volume_details(request, pk, vol_pk):
    volume = get_object_or_404(ProceedingVolume, pk=vol_pk)
    ptype = volume.type

    if ptype.conference_id != pk:
        raise Http404

    if request.method == 'POST':
        form = ProceedingVolumeForm(request.POST, instance=volume)
        if form.is_valid():
            volume = form.save(commit=False)
            volume.save()
            messages.success(request, 'Volume was updated')
            return redirect('conferences:volume-details', pk=pk, vol_pk=vol_pk)
    else:
        form = ProceedingVolumeForm(instance=volume)
    return render(request, 'conferences/form.html', {
        'conference': ptype.conference,
        'form': form,
        'subtitle': 'Edit volume #{}'.format(vol_pk),
        'title': f'Conference #{ptype.conference_id}',
        'back_url': reverse('conferences:proceedings-update',
                            kwargs={'pk': pk, 'proc_pk': ptype.pk}),
    })


@chair_required
@require_POST
def proceeding_volume_delete(request, pk, vol_pk):
    volume = get_object_or_404(ProceedingVolume, pk=vol_pk)
    proc_pk = volume.type_id
    volume.delete()
    messages.warning(request, 'Deleted volume')
    return redirect('conferences:proceedings-update', pk=pk, proc_pk=proc_pk)


@chair_required
def artifact_create(request, pk, proc_pk):
    ptype = get_object_or_404(ProceedingType, pk=proc_pk)
    if request.method == 'POST':
        form = ArtifactDescriptorForm(request.POST)
        if form.is_valid():
            artifact = form.save(commit=False)
            artifact.proc_type = ptype
            artifact.save()
            messages.success(request, 'Artifact was created')
            return redirect('conferences:proceedings-update',
                            pk=pk, proc_pk=proc_pk)
    else:
        form = ArtifactDescriptorForm()
    return render(request, 'conferences/form.html', {
        'conference': ptype.conference,
        'form': form,
        'subtitle': 'New artifact',
        'title': f'Conference #{ptype.conference_id}',
    })


@chair_required
def artifact_details(request, pk, art_pk):
    artifact = get_object_or_404(ArtifactDescriptor, pk=art_pk)
    ptype = artifact.proc_type

    if ptype.conference_id != pk:
        raise Http404

    if request.method == 'POST':
        form = ArtifactDescriptorForm(request.POST, instance=artifact)
        if form.is_valid():
            artifact = form.save(commit=False)
            artifact.save()
            messages.success(request, 'Artifact was updated')
            return redirect('conferences:artifact-details', pk=pk,
                            art_pk=art_pk)
    else:
        form = ArtifactDescriptorForm(instance=artifact)
    return render(request, 'conferences/form.html', {
        'conference': ptype.conference,
        'form': form,
        'subtitle': 'Edit artifact #{}'.format(art_pk),
        'title': f'Conference #{ptype.conference_id}',
        'back_url': reverse('conferences:proceedings-update',
                            kwargs={'pk': pk, 'proc_pk': ptype.pk}),
    })


@chair_required
@require_POST
def artifact_delete(request, pk, art_pk):
    artifact = get_object_or_404(ArtifactDescriptor, pk=art_pk)
    proc_pk = artifact.proc_type_id
    artifact.delete()
    messages.warning(request, 'Deleted artifact')
    return redirect('conferences:proceedings-update', pk=pk, proc_pk=proc_pk)


@chair_required
@require_POST
def artifact_toggle_editable(request, pk, art_pk):
    artifact = get_object_or_404(ArtifactDescriptor, pk=art_pk)
    artifact.editable = not artifact.editable
    artifact.save()
    messages.success(request, 'Updated artifact')
    return redirect('conferences:proceedings-update', pk=pk,
                    proc_pk=artifact.proc_type_id)


@chair_required
def submission_type_create(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    if request.method == 'POST':
        form = SubmissionTypeForm(request.POST, request.FILES)
        if form.is_valid():
            stype = form.save(commit=False)
            stype.conference = conference
            stype.save()
            messages.success(
                request, f'Submission type #{stype.pk} was created'
            )
            return redirect('conferences:details', pk=pk)
    else:
        form = SubmissionTypeForm()
    return render(request, 'conferences/form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Define New Submission Type',
        'title': f'{conference.short_name} Conference',
    })


@chair_required
def submission_type_update(request, pk, sub_pk):
    stype = get_object_or_404(SubmissionType, pk=sub_pk)
    conference = stype.conference
    if conference.pk != pk:
        raise Http404
    if request.method == 'POST':
        form = SubmissionTypeForm(request.POST, request.FILES, instance=stype)
        if form.is_valid():
            form.save()
            messages.success(request, f'{stype.name} updated')
            return redirect('conferences:stype-update', pk=pk, sub_pk=sub_pk)
    else:
        form = SubmissionTypeForm(instance=stype)
    return render(request, 'conferences/form.html', {
        'conference': conference,
        'form': form,
        'subtitle': f'Edit Submission Type',
        'title': f'{conference.short_name} Conference',
    })


@chair_required
@require_POST
def submission_type_delete(request, pk, sub_pk):
    stype = get_object_or_404(SubmissionType, pk=sub_pk)
    form = DeleteForm(stype, request.POST)
    form.save()
    messages.success(request, f'Deleted submission type')
    return redirect('conferences:details', pk=pk)


################################
# TOPICS

@chair_required
def topics_list(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    topics_reorder_form = TopicsReorderForm(conference, ',')
    if request.method == 'POST':
        create_topic_form = TopicCreateForm(conference, request.POST)
        if create_topic_form.is_valid():
            topic = create_topic_form.save()
            messages.success(request, f'Added new topic "{topic.name}"')
            return redirect('conferences:topics', pk=pk)
    else:
        create_topic_form = TopicCreateForm(conference)

    return render(request, 'conferences/topics.html', {
        'conference': conference,
        'form': create_topic_form,
        'reorder_form': topics_reorder_form,
    })


@chair_required
@require_POST
def topic_delete(request, pk, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    conference = get_object_or_404(Conference, pk=pk)
    if conference.pk != topic.conference.pk:
        raise Http404
    name = topic.name
    form = DeleteForm(topic, request.POST)
    if form.is_valid():
        messages.warning(request, f'Topic "{name}" was deleted')
        form.save()
    return redirect('conferences:topics', pk=conference.pk)


@chair_required
@require_POST
def topic_update(request, pk, topic_pk):
    topic = get_object_or_404(Topic, pk=topic_pk)
    conference = get_object_or_404(Conference, pk=pk)
    if conference.pk != topic.conference.pk:
        raise Http404
    form = TopicEditForm(request.POST, instance=topic)
    if form.is_valid():
        messages.success(request, f'Topic "{topic.name}" was updated')
        form.save()
    return redirect('conferences:topics', pk=conference.pk)


@chair_required
@require_POST
def topics_reorder(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    form = TopicsReorderForm(conference, ',', request.POST)
    if form.is_valid():
        form.save()
    return redirect('conferences:topics', pk=pk)
