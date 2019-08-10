from pprint import pprint

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Template, Context
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from markdown import markdown

from chair.utility import validate_chair_access
from chair_mail.context import get_user_context, USER_VARS, \
    get_conference_context, CONFERENCE_VARS, get_submission_context, \
    SUBMISSION_VARS
from chair_mail.forms import EmailFrameUpdateForm, EmailFrameTestForm, \
    EmailTemplateForm, PreviewUserMessageForm, PreviewSubmissionMessageForm
from chair_mail.models import EmailSettings, EmailFrame, EmailTemplate, \
    EmailMessage, GroupEmailMessage
from chair_mail.utility import get_email_frame, get_email_frame_or_404
from conferences.models import Conference
from submissions.models import Submission
from users.models import User


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
    return render(request, 'chair_mail/tab_pages/sent_messages.html', context={
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
    msg = get_object_or_404(GroupEmailMessage, pk=msg_pk)
    template = msg.template
    if request.is_ajax():
        return JsonResponse({
            'body': template.body,
            'subject': template.subject,
            'sent_at': msg.sent_at,
            'sent_by': msg.sent_by.pk,
            'users_to': list(msg.users_to.values_list('pk')),
        })
    return render(
        request, 'chair_mail/tab_pages/group_message_details.html', context={
            'conference': conference,
            'conf_pk': conference.pk,
            'msg': msg,
            'hide_tabs': True,
        })


def compose_to_user(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user_to = get_object_or_404(User, pk=user_pk)

    if request.method == 'POST':
        next_url = request.POST.get(
            'next', reverse('chair:home', kwargs={'conf_pk': conf_pk}))
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(
                conference=conference,
                msg_type=EmailTemplate.TYPE_USER,
                sender=request.user
            )
            context = get_conference_context(conference)
            user_context = {user_to: get_user_context(user_to, conference)}
            message = GroupEmailMessage.create(template, [user_to])
            message.send(request.user, context, user_context)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        form = EmailTemplateForm()
        next_url = request.GET['next']

    variables = CONFERENCE_VARS + USER_VARS
    preview_form = PreviewUserMessageForm(users=[user_to])
    preview_url = reverse('chair_mail:api-render-preview-user', kwargs={
        'conf_pk': conf_pk, 'user_pk': user_pk,
    })
    print(preview_url)
    return render(
        request, 'chair_mail/compose/compose_to_user.html', context={
            'msg_form': form,
            'msg_type': EmailTemplate.TYPE_USER,
            'conference': conference,
            'next': next_url,
            'variables': variables,
            'user_to': user_to,
            'preview_form': preview_form,
            'preview_url': preview_url,
        })


@require_GET
def render_user_message_preview(request, conf_pk, user_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    user_to = get_object_or_404(User, pk=user_pk)
    form = PreviewUserMessageForm(request.GET, users=[user_to])
    if form.is_valid():
        data = form.render_html(conference)
        return JsonResponse(data)
    print('form is invalid: ', form)
    return JsonResponse({}, status=400)


def compose_to_submission(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)
    authors = submission.authors
    users_to = User.objects.filter(pk__in=authors.values('user__pk'))
    preview_form = PreviewSubmissionMessageForm(users=users_to)

    if request.method == 'POST':
        next_url = request.POST.get(
            'next', reverse('chair:home', kwargs={'conf_pk': conf_pk}))
        msg_form = EmailTemplateForm(request.POST)
        if msg_form.is_valid():
            template = msg_form.save(
                conference=conference,
                msg_type=EmailTemplate.TYPE_USER,
                sender=request.user
            )
            context = {
                **get_conference_context(conference),
                **get_submission_context(submission),
            }
            user_context = {
                u: get_user_context(u, conference) for u in users_to
            }
            message = GroupEmailMessage.create(template, users_to)
            message.send(request.user, context, user_context)
            return redirect(next_url)
        else:
            messages.error(request, 'Error sending message')
    else:
        msg_form = EmailTemplateForm()
        next_url = request.GET['next']

    variables = CONFERENCE_VARS + USER_VARS
    return render(
        request, 'chair_mail/compose/compose_to_submission.html', context={
            'msg_form': msg_form,
            'msg_type': EmailTemplate.TYPE_SUBMISSION,
            'conference': conference,
            'next': next_url,
            'variables': variables,
            'submission': submission,
            'preview_form': preview_form,
        })


@require_GET
def render_submission_message_preview(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = get_object_or_404(Submission, pk=sub_pk)
    authors = submission.authors
    users_to = User.objects.filter(pk__in=authors.values('user__pk'))
    form = PreviewSubmissionMessageForm(request.GET, users=users_to)
    if form.is_valid():
        user = User.objects.get(pk=form.cleaned_data['user'])
        ctx = {
            **get_conference_context(conference),
            **get_submission_context(submission),
            **get_user_context(user, conference),
        }
        body_html = markdown(form.cleaned_data['body'])
        body_html = Template(body_html).render(Context(ctx, autoescape=False))
        return JsonResponse({
            'body': body_html,
        })
    return JsonResponse({}, status=400)


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
