import mimetypes

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden, \
    HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET

from conferences.models import Conference
from conferences.utilities import validate_chair_access
from submissions.forms import CreateSubmissionForm, SubmissionDetailsForm, \
    AuthorCreateForm, AuthorsReorderForm, AuthorDeleteForm, \
    UploadReviewManuscriptForm, InviteAuthorForm, UploadAttachmentForm, \
    UpdateSubmissionStatusForm
from submissions.models import Submission, Author, Attachment
from submissions.utilities import is_authorized_edit, \
    is_authorized_view_attachment


def _create_submission(request, form):
    if request.method == 'POST':
        if form.is_valid():
            submission = form.save()

            # Set creator and create first author:
            submission.created_by = request.user
            submission.save()
            Author.objects.create(
                submission=submission,
                order=1,
                user=request.user
            )

            messages.success(request, f'Created submission #{submission.pk}')
            return redirect('submissions:details', pk=submission.pk)

    return render(request, 'submissions/create.html', {
        'form': form,
    })


@login_required
def create_submission(request):
    if request.method == 'POST':
        form = CreateSubmissionForm(request.POST)
    else:
        form = CreateSubmissionForm()
    return _create_submission(request, form)


@login_required
def create_submission_for(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    if request.method == 'POST':
        form = CreateSubmissionForm(request.POST)
    else:
        form = CreateSubmissionForm(initial={'conference': conference.pk})
    return _create_submission(request, form)


@login_required
def submission_details(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.is_viewable_by(request.user):
        if request.method == 'POST':
            if submission.details_editable_by(request.user):
                form = SubmissionDetailsForm(request.POST, instance=submission)
                if form.is_valid():
                    form.save()
                    if submission.reached_overview:
                        return redirect('submissions:overview', pk=pk)
                    return redirect('submissions:authors', pk=pk)
            else:
                return HttpResponseForbidden()
        else:
            form = SubmissionDetailsForm(instance=submission)
        return render(request, 'submissions/details.html', {
            'submission': submission,
            'form': form,
        })
    return HttpResponseForbidden()


@login_required
def submission_authors(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.is_viewable_by(request.user):
        return render(request, 'submissions/authors.html', {
            'submission': submission,
        })
    return HttpResponseForbidden()


@login_required
def edit_manuscript(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.is_viewable_by(request.user):
        if request.method == 'POST':
            if submission.review_manuscript_editable_by(request.user):
                form = UploadReviewManuscriptForm(
                    request.POST,
                    request.FILES,
                    instance=submission
                )
                # We save current file (if any) for two reasons:
                # 1) if this file is not empty and user uploaded a new file, we
                #    are going to delete this old file (in case of valid form);
                #    and
                # 2) it is going to be assigned instead of TemporaryUploadedFile
                #    object in case of form validation error.
                old_file = (submission.review_manuscript.file
                            if submission.review_manuscript else None)
                if form.is_valid():
                    # If the form is valid and user provided a new file, we
                    # delete original file first. Otherwise Django will add a
                    # random suffix which will break our storage strategy.
                    if old_file and request.FILES:
                        submission.review_manuscript.storage.delete(
                            old_file.name
                        )
                    form.save()
                    return redirect('submissions:overview', pk=pk)
                else:
                    # If the form is invalid (e.g. title is not provided),
                    # but the user tried to upload a file, a new
                    # TemporaryUploadedFile object will be created and,
                    # which is more important, it will be assigned to
                    # `note.document` field. We want to avoid this to make sure
                    # that until the form is completely valid previous file
                    # is not re-written. To do it we assign the `old_file`
                    # value to both cleaned_data and note.document:
                    form.cleaned_data['review_manuscript'] = old_file
                    submission.review_manuscript.document = old_file
            else:
                return HttpResponseForbidden()
        else:
            form = UploadReviewManuscriptForm(instance=submission)
        return render(request, 'submissions/manuscript.html', {
            'submission': submission,
            'form': form,
        })
    return HttpResponseForbidden()


@login_required
@require_POST
def delete_manuscript(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.review_manuscript_editable_by(request.user):
        file_name = submission.get_review_manuscript_name()
        if submission.review_manuscript:
            submission.review_manuscript.delete()
        return render(
            request,
            'submissions/components/file_deleted_message.html', {
                'alert_class': 'warning',
                'file_name': file_name,
            })
    else:
        return HttpResponseForbidden()


@login_required
@require_GET
def download_manuscript(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.is_manuscript_viewable_by(request.user):
        if submission.review_manuscript:
            filename = submission.get_review_manuscript_name()
            mtype = mimetypes.guess_type(filename)[0]
            response = HttpResponse(
                submission.review_manuscript.file,
                content_type=mtype
            )
            response['Content-Disposition'] = f'filename={filename}'
            return response
        raise Http404
    return HttpResponseForbidden()


@login_required
def submission_overview(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    deadline = ''

    # If the overview page is visited for the first time, we display finish
    # flag. For the following visits, show close:
    show_finish = not submission.reached_overview
    if show_finish:
        submission.reached_overview = True
        submission.save()
        messages.success(
            request,
            f'Submission #{pk} "{submission.title}" was successfully created!'
        )

    if submission.is_viewable_by(request.user):
        return render(request, 'submissions/overview.html', {
            'submission': submission,
            'deadline': deadline,
            'show_finish': show_finish,
        })
    return HttpResponseForbidden()


@login_required
@require_POST
def submission_delete(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.is_deletable_by(request.user):
        # TODO: send letters to authors
        messages.warning(
            request,
            f'Submission #{pk} "{submission.title}" was deleted'
        )
        if submission.review_manuscript:
            submission.review_manuscript.delete()
        submission.delete()
        return redirect('home')
    return HttpResponseForbidden()


#
# Authors:
#
@login_required
@require_POST
def delete_author(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.authors_editable_by(request.user):
        form = AuthorDeleteForm(submission, request.POST)
        if form.is_valid():
            form.save()
        return redirect('submissions:authors', pk=pk)
    return HttpResponseForbidden()


@login_required
@require_POST
def create_author(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.authors_editable_by(request.user):
        form = AuthorCreateForm(submission, request.POST)
        if form.is_valid():
            form.save()
        return redirect('submissions:authors', pk=pk)
    return HttpResponseForbidden()


@login_required
@require_POST
def order_authors(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.authors_editable_by(request.user):
        form = AuthorsReorderForm(submission, request.POST)
        if form.is_valid():
            form.save()
        return redirect('submissions:authors', pk=pk)
    return HttpResponseForbidden()


@login_required
@require_POST
def send_invitation(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.authors_editable_by(request.user):
        form = InviteAuthorForm(request.POST)
        if form.is_valid():
            form.save(request, submission)
            messages.success(request, _('Invitation sent'))
        else:
            messages.warning(request, _('Errors while sending invitation'))
        return redirect('submissions:authors', pk=pk)
    return HttpResponseForbidden()


@login_required
@require_GET
def camera_ready(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.status not in [Submission.ACCEPTED, Submission.IN_PRINT,
                                 Submission.PUBLISHED]:
        raise Http404
    return render(request, 'submissions/camera_ready.html', context={
        'submission': submission,
        'editable': True,
    })


@login_required
@require_GET
def download_attachment(request, pk, att_pk):
    submission = get_object_or_404(Submission, pk=pk)
    attachment = Attachment.objects.get(pk=att_pk)
    if not is_authorized_view_attachment(request.user, submission):
        return HttpResponseForbidden()
    if attachment.file:
        filename = attachment.get_file_name()
        mtype = mimetypes.guess_type(filename)[0]
        # TODO: add mime-type checking
        response = HttpResponse(attachment.file.file, content_type=mtype)
        response['Content-Disposition'] = f'filename={filename}'
        return response
    raise Http404


@login_required
@require_POST
def upload_attachment(request, pk, att_pk):
    submission = get_object_or_404(Submission, pk=pk)
    attachment = get_object_or_404(Attachment, pk=att_pk)
    if not is_authorized_edit(request.user, submission):
        return HttpResponseForbidden()
    form = UploadAttachmentForm(
        request.POST, request.FILES, instance=attachment)
    # We save current file (if any) for two reasons:
    # 1) if this file is not empty and user uploaded a new file, we
    #    are going to delete this old file (in case of valid form);
    #    and
    # 2) it is going to be assigned instead of TemporaryUploadedFile
    #    object in case of form validation error.
    old_file = attachment.file.file if attachment.file else None
    if form.is_valid():
        # If the form is valid and user provided a new file, we
        # delete original file first. Otherwise Django will add a
        # random suffix which will break our storage strategy.
        if old_file and request.FILES:
            attachment.file.storage.delete(old_file.name)
        form.save()
        messages.success(request, f'Uploaded {attachment.name} file '
                                  f'{attachment.get_file_name()}')
    else:
        # If the form is invalid (e.g. title is not provided),
        # but the user tried to upload a file, a new
        # TemporaryUploadedFile object will be created and,
        # which is more important, it will be assigned to
        # `note.document` field. We want to avoid this to make sure
        # that until the form is completely valid previous file
        # is not re-written. To do it we assign the `old_file`
        # value to both cleaned_data and note.document:
        form.cleaned_data['file'] = old_file
        attachment.file.document = old_file
    next_url = request.GET.get('next')
    if next_url:
        return HttpResponseRedirect(next_url)
    return redirect('submissions:camera-ready', pk=pk)


@login_required
@require_POST
def delete_attachment(request, pk, att_pk):
    submission = get_object_or_404(Submission, pk=pk)
    attachment = get_object_or_404(Attachment, pk=att_pk)
    if not is_authorized_edit(request.user, submission):
        return HttpResponseForbidden()
    file_name = attachment.get_file_name()
    if attachment.file:
        attachment.file.delete()
    messages.warning(request, f'Deleted {attachment.name} file {file_name}')
    next_url = request.GET.get('next')
    if next_url:
        return HttpResponseRedirect(next_url)
    return redirect('submissions:camera-ready', pk=pk)


@require_POST
def update_status(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    validate_chair_access(request.user, submission.conference)
    form = UpdateSubmissionStatusForm(request.POST, instance=submission)
    if form.is_valid():
        form.save()
        return JsonResponse({}, status=200)
    return JsonResponse({}, status=500)
