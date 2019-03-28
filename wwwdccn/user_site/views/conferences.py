from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from conferences.decorators import chair_required
from conferences.forms import ConferenceForm
from conferences.models import Conference


@login_required
def conferences_list(request):
    return render(request, 'user_site/conferences/conferences_list.html', {
        'conferences': Conference.objects.all()
    })


def conference_create(request):
    if request.method == 'POST':
        form = ConferenceForm(request.POST)
        if form.is_valid():
            conference = form.save()
            conference.creator = request.user
            conference.save()
            return redirect('conferences-list')
    else:
        form = ConferenceForm()
    return render(request, 'user_site/conferences/conference_create.html', {
        'form': form
    })


@chair_required
def conference_edit(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    if request.method == 'POST':
        form = ConferenceForm(request.POST, instance=conference)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Conference #{pk} "{conference.short_name}" was updated'
            )
            return redirect('conferences-list')
    else:
         form = ConferenceForm(instance=conference)
    return render(request, 'user_site/conferences/conference_edit.html', {
        'conference': conference,
        'form': form,
    })
