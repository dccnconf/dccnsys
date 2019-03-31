from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from submissions.forms import CreateSubmissionForm


@login_required
def create_submission(request):
    if request.method == 'POST':
        print(request.POST)
        form = CreateSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)  #TODO
            messages.success(request, f'Created submission #{submission.pk}')
            return redirect('home')
    else:
        form = CreateSubmissionForm()

    return render(request, 'submissions/submission_create.html', {
        'form': form,
    })
