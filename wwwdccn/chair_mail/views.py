from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access
from chair_mail.context import USER_VARS, CONFERENCE_VARS, SUBMISSION_VARS, \
    FRAME_VARS
from chair_mail.forms import EmailFrameUpdateForm, EmailFrameTestForm, \
    PreviewSubmissionMessageForm, MessageForm, PreviewUserMessageForm
from chair_mail.mailing_lists import ALL_LISTS
from chair_mail.models import EmailSettings, EmailFrame, EmailMessage, \
    GroupMessage, UserMessage, MSG_TYPE_USER, SubmissionMessage, \
    MSG_TYPE_SUBMISSION
from chair_mail.utility import get_email_frame, get_email_frame_or_404
from conferences.models import Conference
from submissions.models import Submission


def _get_grouped_vars(msg_type):
    if msg_type == MSG_TYPE_USER:
        return (
            ('Conference variables', CONFERENCE_VARS),
            ('User variables', USER_VARS)
        )
    elif msg_type == MSG_TYPE_SUBMISSION:
        return (
            ('Conference variables', CONFERENCE_VARS),
            ('User variables', USER_VARS),
            ('Submission variables', SUBMISSION_VARS),
        )
    raise ValueError(f'unrecognized message type "{msg_type}"')


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
        'variables': FRAME_VARS,
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


def create_compose_view(msg_type, preview_form_class, preview_url_name,
                        list_objects_url_name, object_icon_class):
    def handler(request, conf_pk):
        conference = get_object_or_404(Conference, pk=conf_pk)
        validate_chair_access(request.user, conference)
        default_url = reverse('chair:home', kwargs={'conf_pk': conf_pk})

        if request.method == 'POST':
            next_url = request.POST.get('next', default_url)
            form = MessageForm(request.POST)
            if form.is_valid():
                all_objects_to = list(form.cleaned_objects)
                for ml in form.cleaned_lists:
                    all_objects_to.extend(list(ml.query(conference)))

                msg = UserMessage.create(
                    subject=form.cleaned_data['subject'],
                    body=form.cleaned_data['body'],
                    conference=conference,
                    objects_to=list(set(all_objects_to)),
                )
                msg.send(sender=request.user)
                return redirect(next_url)
            else:
                messages.error(request, 'Error sending message')
        else:
            form = MessageForm(initial={
                'objects': request.GET.get('objects', ''),
                'lists': request.GET.get('lists', ''),
            })
            next_url = request.GET.get('next', default_url)

        variables = _get_grouped_vars(msg_type)
        preview_form = preview_form_class()
        preview_url = reverse(preview_url_name, kwargs={'conf_pk': conf_pk})
        list_objects_url = reverse(
            list_objects_url_name, kwargs={'conf_pk': conf_pk})
        return render(
            request, 'chair_mail/compose/compose.html', context={
                'msg_form': form,
                'msg_type': msg_type,
                'conference': conference,
                'next': next_url,
                'variables': variables,
                'preview_url': preview_url,
                'preview_form': preview_form,
                'list_objects_url': list_objects_url,
                'object_icon_class': object_icon_class,
            })
    return handler


compose_user = create_compose_view(
    msg_type=MSG_TYPE_USER,
    preview_form_class=PreviewUserMessageForm,
    preview_url_name='chair_mail:render-preview-user',
    list_objects_url_name='chair_mail:list-users',
    object_icon_class='fas fa-user',
)

compose_submission = create_compose_view(
    msg_type=MSG_TYPE_SUBMISSION,
    preview_form_class=PreviewSubmissionMessageForm,
    preview_url_name='chair_mail:render-preview-submission',
    list_objects_url_name='chair_mail:list-submissions',
    object_icon_class='fas fa-scroll',
)


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
