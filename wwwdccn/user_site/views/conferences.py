from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from conferences.decorators import chair_required
from conferences.forms import ConferenceForm, SubmissionStageForm, \
    ReviewStageForm
from conferences.models import Conference


@login_required
def conferences_list(request):
    return render(request, 'user_site/conferences/conferences_list.html', {
        'conferences': Conference.objects.all()
    })


@login_required
def conference_details(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    return render(request, 'user_site/conferences/conference_details.html', {
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
            return redirect('conference-details', pk=conference.pk)
    else:
        form = ConferenceForm()
    return render(request, 'user_site/conferences/conference_create.html', {
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
            return redirect('conference-details', pk=pk)
    else:
         form = ConferenceForm(instance=conference)
    return render(request, 'user_site/conferences/conference_form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Settings',
        'title': f'Edit conference #{pk}',
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
            return redirect('conference-details', pk=pk)
    else:
        form = SubmissionStageForm(instance=stage)
    return render(request, 'user_site/conferences/conference_form.html', {
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
            return redirect('conference-details', pk=pk)
    else:
        form = ReviewStageForm(instance=stage)
    return render(request, 'user_site/conferences/conference_form.html', {
        'conference': conference,
        'form': form,
        'subtitle': 'Reviews Stage',
        'title': f'Edit conference #{pk}',
    })
