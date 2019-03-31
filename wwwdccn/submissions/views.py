from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from submissions.forms import CreateSubmissionForm, SubmissionDetailsForm
from submissions.models import Submission, Author


@login_required
def create_submission(request):
    if request.method == 'POST':
        print(request.POST)
        form = CreateSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save()

            # Set creator and create first author:
            submission.created_by = request.user
            Author.objects.create(
                submission=submission,
                order=1,
                user=request.user
            )

            messages.success(request, f'Created submission #{submission.pk}')
            return redirect('submission-details', pk=submission.pk)
    else:
        form = CreateSubmissionForm()

    return render(request, 'submissions/submission_create.html', {
        'form': form,
    })


@login_required
def submission_details(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if request.method == 'POST':
        form = SubmissionDetailsForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = SubmissionDetailsForm(instance=submission)
    return render(request, 'submissions/submission_details.html', {
        'submission': submission,
        'form': form,
    })


@login_required
def submission_authors(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    return render(request, 'submissions/submission_authors.html', {
        'submission': submission,
    })


@login_required
def submission_manuscript(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    return render(request, 'submissions/submission_manuscript.html', {
        'submission': submission,
    })


@login_required
def submission_overview(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    return render(request, 'submissions/submission_overview.html', {
        'submission': submission,
    })