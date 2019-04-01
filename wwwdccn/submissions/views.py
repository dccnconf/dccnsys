from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from submissions.forms import CreateSubmissionForm, SubmissionDetailsForm, \
    AuthorCreateForm, AuthorsReorderForm, AuthorDeleteForm
from submissions.models import Submission, Author

# TODO: check in views that user has rights to view/edit given submission


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
            submission.save()

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
            return redirect('submission-authors', pk=pk)
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


@login_required
@require_POST
def submission_delete(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    # TODO: send letters to authors
    submission.delete()
    return redirect('home')


#
# Authors:
#
@login_required
@require_POST
def submission_author_delete(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    form = AuthorDeleteForm(submission, request.POST)
    if form.is_valid():
        form.save()
    return redirect('submission-authors', pk=pk)


@login_required
@require_POST
def submission_author_create(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    form = AuthorCreateForm(submission, request.POST)
    if form.is_valid():
        form.save()
    else:
        print(form.errors)
    return redirect('submission-authors', pk=pk)

@login_required
@require_POST
def submission_authors_reorder(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    form = AuthorsReorderForm(submission, ',', request.POST)
    if form.is_valid():
        form.save()
    return redirect('submission-authors', pk=pk)
