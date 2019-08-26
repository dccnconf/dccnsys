from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from chair.utility import validate_chair_access
from chair_mail.context import USER_VARS, CONFERENCE_VARS, SUBMISSION_VARS, \
    FRAME_VARS
from chair_mail.forms import EmailFrameUpdateForm, EmailFrameTestForm, \
    MessageForm, get_preview_form_class, EditNotificationForm, \
    UpdateNotificationStateForm
from chair_mail.mailing_lists import ALL_LISTS
from chair_mail.models import EmailSettings, EmailFrame, EmailMessage, \
    GroupMessage, MSG_TYPE_USER, MSG_TYPE_SUBMISSION, get_group_message_model, \
    get_message_leaf_model, SystemNotification, DEFAULT_NOTIFICATIONS_DATA
from chair_mail.utility import get_email_frame, get_email_frame_or_404, \
    reverse_preview_url, reverse_list_objects_url, get_object_name, \
    get_object_url
from conferences.models import Conference


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
    leaf_msg = get_message_leaf_model(msg)
    recipients = [{
        'name': get_object_name(leaf_msg.message_type, obj),
        'url': get_object_url(leaf_msg.message_type, conference, obj),
    } for obj in leaf_msg.recipients.all()]

    if request.is_ajax():
        return JsonResponse({
            'body': msg.body,
            'subject': msg.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
        })
    return render(
        request, 'chair_mail/tab_pages/message_details.html', context={
            'conference': conference,
            'conf_pk': conference.pk,
            'msg': msg,
            'hide_tabs': True,
            'recipients': recipients,
        })


def create_compose_view(msg_type, object_icon_class):
    preview_form_class = get_preview_form_class(msg_type)
    message_class = get_group_message_model(msg_type)

    def handler(request, conf_pk):
        conference = get_object_or_404(Conference, pk=conf_pk)
        validate_chair_access(request.user, conference)
        default_next_url = reverse('chair:home', kwargs={'conf_pk': conf_pk})

        if request.method == 'POST':
            next_url = request.POST.get('next', default_next_url)
            form = MessageForm(request.POST, msg_type=msg_type)
            if form.is_valid():
                all_objects_to = list(form.cleaned_objects)
                for ml in form.cleaned_lists:
                    all_objects_to.extend(list(ml.query(conference)))
                msg = message_class.create(
                    subject=form.cleaned_data['subject'],
                    body=form.cleaned_data['body'],
                    conference=conference,
                    objects_to=list(set(all_objects_to)),
                )
                msg.send(sender=request.user)
                return redirect(next_url)
            else:
                errors = form.non_field_errors()
                if len(errors) == 1:
                    messages.error(request, errors[0])
                elif len(errors) > 1:
                    messages.error(request, errors)
                else:
                    messages.error(request, 'Error sending message')
        else:
            form = MessageForm(initial={
                'objects': request.GET.get('objects', ''),
                'lists': request.GET.get('lists', ''),
            }, msg_type=msg_type)
            next_url = request.GET.get('next', default_next_url)

        return render(
            request, 'chair_mail/compose/compose.html', context={
                'msg_form': form,
                'msg_type': msg_type,
                'conference': conference,
                'next': next_url,
                'variables': _get_grouped_vars(msg_type),
                'preview_url': reverse_preview_url(msg_type, conference),
                'preview_form': preview_form_class(),
                'list_objects_url':
                    reverse_list_objects_url(msg_type, conference),
                'object_icon_class': object_icon_class,
            })
    return handler


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
    return render(
        request, 'chair_mail/preview_pages/email_message_preview.html',
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


@require_POST
def delete_all_messages(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    num_group_messages = GroupMessage.objects.count()
    num_email_messages = EmailMessage.objects.count()
    GroupMessage.objects.all().delete()
    EmailMessage.objects.all().delete()
    messages.success(
        request, f'Deleted {num_group_messages} group messages and '
                 f'{num_email_messages} messages instances'
    )
    return redirect('chair_mail:sent-messages', conf_pk=conf_pk)


@require_GET
def render_frame_preview(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    frame = get_email_frame(conference)
    if frame:
        body = f"<p>Dear {request.user.profile.get_full_name()},</p>" \
               f"<p>this is a frame preview.</p>"
        subject = 'Frame preview'
        html = frame.render_html(subject, body)
        return HttpResponse(html)
    return HttpResponse()


#
# Notifications
#
@require_GET
def notifications_list(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    return render(request, 'chair_mail/tab_pages/notifications.html', context={
        'conference': conference,
        'active_tab': 'notifications',
    })


@require_POST
def reset_all_notifications(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    # Purging all existing notifications:
    conference.notifications.all().delete()
    # Creating default notifications:
    for name, kwargs in DEFAULT_NOTIFICATIONS_DATA.items():
        SystemNotification.objects.create(name=name, conference=conference,
                                          **kwargs)
    return redirect('chair_mail:notifications', conf_pk)


@require_POST
def reset_notification(request, conf_pk, notif_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    notification = get_object_or_404(SystemNotification, pk=notif_pk)
    data = DEFAULT_NOTIFICATIONS_DATA[notification.name]
    notification.subject = data['subject']
    notification.type = data['type']
    notification.body = data['body']
    notification.save()
    return redirect('chair_mail:notifications', conf_pk)


def notification_details(request, conf_pk, notif_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    notification = get_object_or_404(SystemNotification, pk=notif_pk)
    if request.method == 'POST':
        notif_form = EditNotificationForm(request.POST, instance=notification)
        if notif_form.is_valid():
            notif_form.save()
            messages.success(request, 'Your changes were saved')
            return redirect(
                'chair_mail:notification-details', conf_pk, notif_pk)
    else:
        notif_form = EditNotificationForm(instance=notification)

    return render(
        request, 'chair_mail/tab_pages/notification_details.html', context={
            'conference': conference,
            'notification': notification,
            'hide_tabs': True,
            'notif_form': notif_form,
            'variables': _get_grouped_vars(notification.type),
            'preview_url': reverse_preview_url(notification.type, conference),
            'preview_form': get_preview_form_class(notification.type)(),
            'list_objects_url':
                reverse_list_objects_url(notification.type, conference),
        })


@require_POST
def update_notification_state(request, conf_pk, notif_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    notification = get_object_or_404(SystemNotification, pk=notif_pk)
    form = UpdateNotificationStateForm(request.POST, instance=notification)
    if form.is_valid():
        form.save()
    return redirect('chair_mail:notifications', conf_pk)
