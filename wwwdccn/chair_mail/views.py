from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access
from chair_mail.context import USER_VARS, CONFERENCE_VARS, SUBMISSION_VARS
from chair_mail.forms import EmailFrameUpdateForm, EmailFrameTestForm, \
    PreviewSubmissionMessageForm, MessageForm, UserMessageForm
from chair_mail.mailing_lists import ALL_LISTS
from chair_mail.models import EmailSettings, EmailFrame, EmailMessage, \
    GroupMessage, UserMessage, MSG_TYPE_USER, SubmissionMessage, \
    MSG_TYPE_SUBMISSION
from chair_mail.utility import get_email_frame, get_email_frame_or_404
from conferences.models import Conference
from submissions.models import Submission


@require_GET
def overview(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame(conference)
    return render(request, 'chair_mail/tab_pages/overview.html', context={
        'conference': conference,
        'frame': frame,
        'active_tab': 'overview',
    })


@require_POST
def create_frame(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    if not hasattr(conference, 'email_settings'):
        EmailSettings.objects.create(conference=conference)
        messages.success(request, 'Created email settings')
    email_settings = conference.email_settings
    frame = email_settings.frame
    template_html = get_template(
        'chair_mail/email/default_frame_html.html').template
    template_plain = get_template(
        'chair_mail/email/default_frame_plain.txt').template
    if frame:
        frame.text_html = template_html.source
        frame.text_plain = template_plain.source
        frame.created_at = timezone.now()
        frame.updated_at = timezone.now()
        frame.created_by = request.user
        frame.save()
        messages.success(request, 'Reset existing frame')
    else:
        frame = EmailFrame.objects.create(
            conference=conference,
            created_by=request.user,
            text_plain=template_plain.source,
            text_html=template_html.source,
        )
        email_settings.frame = frame
        email_settings.save()
        messages.success(request, 'Created new template')

    default_next = reverse('chair_mail:overview', kwargs={'conf_pk': conf_pk})
    next_url = request.GET.get('next', default_next)
    return redirect(next_url)


def frame_details(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame_or_404(conference)

    if request.method == 'POST':
        form = EmailFrameUpdateForm(request.POST, instance=frame)
        if form.is_valid():
            form.save()
            return redirect('chair_mail:frame-details', conf_pk=conf_pk)
    else:
        form = EmailFrameUpdateForm(instance=frame)

    return render(request, 'chair_mail/tab_pages/frame_details.html', context={
        'conference': conference,
        'frame': frame,
        'active_tab': 'frame',
        'form': form,
    })


@require_GET
def sent_messages(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame(conference)
    msg_list = conference.sent_group_emails.all().order_by('-sent_at')
    return render(request, 'chair_mail/tab_pages/messages.html', context={
        'conference': conference,
        'active_tab': 'messages',
        'frame': frame,
        'msg_list': msg_list,
    })


@require_POST
def send_frame_test_message(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    form = EmailFrameTestForm(request.POST)
    if form.is_valid():
        form.send_message(request.user, conference)
        return JsonResponse({'email': request.user.email})
    resp = JsonResponse({'email': request.user.email})
    resp.status_code = 400
    return resp


@require_GET
def group_message_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(GroupMessage, pk=msg_pk)
    if request.is_ajax():
        return JsonResponse({
            'body': msg.body,
            'subject': msg.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'users_to': [],  # TODO
        })
    return render(
        request, 'chair_mail/tab_pages/group_message_details.html', context={
            'conference': conference,
            'conf_pk': conference.pk,
            'msg': msg,
            'hide_tabs': True,
        })


def compose_user(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    default_url = reverse('chair:home', kwargs={'conf_pk': conf_pk})

    if request.method == 'POST':
        next_url = request.POST.get('next', default_url)
        form = UserMessageForm(request.POST)
        if form.is_valid():
            all_users_to = list(form.cleaned_users)
            for ml in form.cleaned_lists:
                all_users_to.extend(list(ml.query(conference)))
            users_to = list(set(all_users_to))

            msg = UserMessage.create(
                subject=form.cleaned_data['subject'],
                body=form.cleaned_data['body'],
                conference=conference,
                users_to=users_to,
            )
            msg.send(request.user)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        form = UserMessageForm(initial={
            'users': request.GET.get('users', ''),
            'lists': request.GET.get('lists', ''),
        })
        next_url = request.GET.get('next', default_url)

    variables = (
            ('Conference variables', CONFERENCE_VARS),
            ('User variables', USER_VARS)
    )
    preview_url = reverse(
        'chair_mail:render-preview-user', kwargs={'conf_pk': conf_pk})
    return render(
        request, 'chair_mail/compose/compose_to_user.html', context={
            'msg_form': form,
            'msg_type': MSG_TYPE_USER,
            'conference': conference,
            'next': next_url,
            'variables': variables,
            'preview_url': preview_url,
        })


def compose_to_submission(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)

    if request.method == 'POST':
        next_url = request.POST.get(
            'next', reverse('chair:home', kwargs={'conf_pk': conf_pk}))
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = SubmissionMessage.create(
                subject=form.cleaned_data['subject'],
                body=form.cleaned_data['body'],
                conference=conference,
                submissions_to=[submission],
            )
            msg.send(request.user)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        form = MessageForm()
        next_url = request.GET['next']

    variables = SUBMISSION_VARS + CONFERENCE_VARS + USER_VARS
    preview_form = PreviewSubmissionMessageForm(submissions=[submission])
    preview_url = reverse('chair_mail:api-render-preview-submission', kwargs={
        'conf_pk': conf_pk, 'sub_pk': sub_pk,
    })
    return render(
        request, 'chair_mail/compose/compose_to_submission.html', context={
            'msg_form': form,
            'msg_type': MSG_TYPE_SUBMISSION,
            'conference': conference,
            'next': next_url,
            'variables': variables,
            'submission': submission,
            'preview_form': preview_form,
            'preview_url': preview_url,
        })


@require_GET
def render_submission_message_preview(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)
    form = PreviewSubmissionMessageForm(request.GET, submissions=[submission])
    if form.is_valid():
        data = form.render_html(conference)
        return JsonResponse(data)
    return JsonResponse({}, status=400)


@require_GET
def get_compose_form_components(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    list_name = request.GET['mailing_list']
    ml = [l for l in ALL_LISTS if l.name == list_name][0]
    return JsonResponse({
        'type': ml.type,
        'preview_form': '',  # TODO
        'vars': '',  # TODO
    })


@require_GET
def message_details(request, conf_pk, msg_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    msg = get_object_or_404(EmailMessage, pk=msg_pk)
    if request.is_ajax():
        return JsonResponse({
            'text_html': msg.text_html,
            'text_plain': msg.text_plain,
            'subject': msg.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'user_to': msg.user_to.pk,
        })
    next_url = request.GET.get('next', default='')
    return render(request,
                  'chair_mail/preview_pages/email_message_preview.html',
                  context={
                      'conference': conference,
                      'msg': msg,
                      'next': next_url,
                  })


def help_compose(request):
    return render(request, 'chair_mail/compose/help.html', context={
        'variables': (
            ('User variables', USER_VARS),
            ('Submission variables', SUBMISSION_VARS),
            ('Conference variables', CONFERENCE_VARS),
        ),
        'mailing_lists': ALL_LISTS,
    })
