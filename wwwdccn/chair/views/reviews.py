import statistics

from django.http import HttpResponse
from django.utils.datetime_safe import datetime
from docx import Document
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.shared import Cm

from chair.utility import validate_chair_access, build_paged_view_context
from conferences.models import Conference
from review.forms import UpdateDecisionForm
from review.models import Decision
from submissions.models import Submission
from users.models import User

import logging
logger = logging.getLogger(__name__)

QUALITY_COLOR = {
    'excellent': 'success',
    'good': 'info',
    'average': 'warning-13',
    'poor': 'danger',
    '?': 'danger',
}

QUALITY_ICON_CLASS = {
    'excellent': 'far fa-grin-stars',
    'good': 'far fa-smile',
    'average': 'far fa-meh',
    'poor': 'far fa-frown',
    '?': 'fas fa-question',
}


def get_review_stats(conference, stype=None):
    submissions = conference.submission_set.exclude(status=Submission.SUBMITTED)
    if stype is not None:
        submissions = submissions.filter(stype=stype)

    reviews = {sub: sub.reviews.all() for sub in submissions}
    num_reviews_required = {
        st.pk: st.num_reviews
        for st in conference.submissiontype_set.all()
    }

    def get_num_reviews_required(sub):
        return num_reviews_required[sub.stype_id] if sub.stype else 0

    rev_stats = {
        sub: {
            'num_required': get_num_reviews_required(sub),
            'num_assigned': reviews[sub].count(),
        } for sub in submissions
    }

    all_scores = []
    for sub in submissions:
        record = rev_stats[sub]
        assigned = reviews[sub]
        finished = assigned.filter(submitted=True)
        num_finished = finished.count()
        scores = [r.average_score() if r.submitted else 0 for r in assigned]

        record['assigned_reviews'] = assigned
        record['finished_reviews'] = finished
        record['num_finished'] = num_finished
        record['complete'] = num_finished >= record['num_required']
        record['scores_list'] = scores

        if record['complete']:
            record['score'] = sum(x for x in scores) / len(scores)
            all_scores.append(record['score'])
        else:
            record['score'] = 0

    #
    # Estimate statistics:
    #
    if all_scores:
        stats = {
            'average': statistics.mean(all_scores),
            'median': statistics.median(all_scores),
        }
    else:
        stats = {'average': 0, 'median': 0}
    upper_median_scores = [sc for sc in all_scores if sc >= stats['median']]
    lower_median_scores = [sc for sc in all_scores if sc < stats['median']]
    if upper_median_scores:
        stats['hq'] = statistics.median(upper_median_scores)
    else:
        stats['hq'] = stats['median']
    if lower_median_scores:
        stats['lq'] = statistics.median(lower_median_scores)
    else:
        stats['lq'] = stats['median']

    #
    # Compute incomplete and not assigned submissions:
    #
    stats['num_not_assigned'] = sum(
        1 if rev_stats[s]['num_assigned'] < rev_stats[s]['num_required'] else 0
        for s in submissions)
    stats['num_assigned_incomplete'] = sum(
        (1 if (rev_stats[s]['num_assigned'] >= rev_stats[s]['num_required'] >
               rev_stats[s]['num_finished']) else 0)
        for s in submissions)
    stats['num_complete'] = sum(
        1 if rev_stats[s]['complete'] else 0 for s in submissions)
    stats['num_review_submissions'] = len(submissions)

    for sub in submissions:
        record = rev_stats[sub]
        if not record['complete']:
            quality = '?'
        else:
            score = record['score']
            if score >= stats['hq']:
                quality = 'excellent'
            elif score >= stats['median']:
                quality = 'good'
            elif score >= stats['lq']:
                quality = 'average'
            else:
                quality = 'poor'
        record['quality'] = quality
        record['score_color'] = QUALITY_COLOR[quality]
        record['icon_class'] = QUALITY_ICON_CLASS[quality]

    return submissions, rev_stats, stats


def _get_decision_form_data(submission):
    decision = submission.review_decision.first()
    proc_type = decision.proc_type if decision else None
    volume = decision.volume if decision else None
    default_option = [('', 'Not selected')]

    # 1) Filling data_decision value and display:
    data_decision = {'hidden': False, 'options': Decision.DECISION_CHOICES}
    decision_value = Decision.UNDEFINED if not decision else decision.decision
    data_decision['value'] = decision_value
    data_decision['display'] = [
        opt[1] for opt in Decision.DECISION_CHOICES if opt[0] == decision_value
    ][0]

    # 2) Fill proceedings type if possible:
    stype = submission.stype
    data_proc_type = {
        'hidden': decision_value != Decision.ACCEPT,
        'value': '', 'display': default_option[0][-1],
    }
    if not data_proc_type['hidden']:
        data_proc_type['options'] = default_option + [
            (pt.pk, pt.name) for pt in stype.possible_proceedings.all()]
        if proc_type:
            data_proc_type.update({
                'value': proc_type.pk, 'display': proc_type.name
            })

    # 3) Fill volumes if possible:
    data_volume = {
        'hidden': data_proc_type['value'] == '',
        'value': '', 'display': default_option[0][-1],
    }
    if not data_volume['hidden']:
        data_volume['options'] = default_option + [
            (vol.pk, vol.name) for vol in proc_type.volumes.all()]
        if volume:
            data_volume.update({'value': volume.pk, 'display': volume.name})

    # 4) Collect everything and output:
    return {
        'decision': data_decision,
        'proc_type': data_proc_type,
        'volume': data_volume,
        'committed': decision.committed if decision else True
    }


@require_GET
def list_submissions(request, conf_pk, page=1):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    submissions, review_stats, global_stats = get_review_stats(conference)

    for sub in submissions:
        record = review_stats[sub]
        record['scores_list_str'] = [
            f'{x:.1f}' if x > 0 else '?' for x in record['scores_list']]
        if record['complete']:
            record['score_str'] = f"{record['score']:.1f}"
        else:
            record['score_str'] = '?'

    scored_submissions = [
        sub for sub in submissions if review_stats[sub]['complete']]
    average_score = 0 if len(scored_submissions) == 0 else (
        sum(review_stats[sub]['score'] for sub in scored_submissions) /
        len(scored_submissions))

    warnings = {}
    for sub in submissions:
        w = []
        stats = review_stats[sub]
        if sub.status == Submission.UNDER_REVIEW:
            num_assigned = stats['num_assigned']
            num_required = stats['num_required']
            num_finished = stats['num_finished']
            if num_assigned < num_required:
                w.append(f'{num_required - num_assigned} reviews not assigned')
            if num_finished < num_assigned:
                w.append(f'{num_assigned - num_finished} reviews incomplete')

        warnings[sub] = w

    submissions = list(submissions)

    items = [{
        'object': sub,
        'title': sub.title,
        'authors': [{
            'name': pr.get_full_name(),
            'user_pk': pr.user.pk,
        } for pr in sub.get_authors_profiles()],
        'pk': sub.pk,
        'status': sub.status,  # this is needed to make `status_class` work
        'status_display': sub.get_status_display(),
        'reviews': review_stats[sub],
        'warnings': warnings[sub],
        'decision_form_data': _get_decision_form_data(sub),
    } for sub in submissions]

    def get_order_key(item):
        sub = item['object']
        rs = review_stats[sub]
        if rs['complete']:
            return rs['score']
        return -(rs['num_required'] - rs['num_finished'])

    items.sort(key=get_order_key, reverse=True)

    context = build_paged_view_context(
        request, items, page, 'chair:reviews-pages', {'conf_pk': conf_pk}
    )
    context.update({
        'conference': conference,
        'average_score': average_score,
        'stats': global_stats,
    })
    return render(request, 'chair/reviews/reviews_list.html',
                  context=context)


def decision_control_panel(request, conf_pk, sub_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    submission = Submission.objects.get(pk=sub_pk)
    decision = submission.review_decision.first()
    if not decision:
        decision = Decision.objects.create(submission=submission)
    form = UpdateDecisionForm(request.POST or None, instance=decision)
    if request.method == 'POST' and form.is_valid():
        print('form is valid!')
        form.save()
    return render(request, 'chair/reviews/_decision_control.html', context={
        'form_data': _get_decision_form_data(submission),
        'conf_pk': conf_pk, 'sub_pk': sub_pk,
    })


@require_GET
def export_doc(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    submissions, reviews, stats = get_review_stats(conference)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    document = Document()
    document.add_heading(f'{conference.short_name} Review Report')
    document.add_paragraph('')  # Just line skip
    table = document.add_table(rows=9, cols=2)
    table.rows[0].cells[0].text = 'Report date'
    table.rows[0].cells[1].text = datetime.now().strftime('%d %b %Y, %H:%M')
    for i, (key, details, dtype) in enumerate(zip(
            ('average', 'lq', 'median', 'hq',
             'num_review_submissions', 'num_complete',
             'num_assigned_incomplete', 'num_not_assigned'),
            ('Average score', 'Q3', 'Q2 (median)', 'Q1',
             'Number of submissions under review',
             'Number of submissions with complete reviews',
             'Number of submissions with assigned, but incomplete reviews',
             'Number of submissions with partially not assigned reviewers'),
            ('float', 'float', 'float', 'float', 'int', 'int', 'int', 'int')
    )):
        table.rows[i + 1].cells[0].text = details
        value = f'{stats[key]:.2f}' if dtype == 'float' else f'{stats[key]}'
        table.rows[i + 1].cells[1].text = value

    # Writing submissions:
    submissions = list(submissions)

    def get_order_key(sub):
        rs = reviews[sub]
        if rs['complete']:
            return rs['score']
        return -(rs['num_required'] - rs['num_finished'])

    submissions.sort(key=get_order_key, reverse=True)

    profiles = {u: u.profile for u in User.objects.all()}
    document.add_page_break()

    for submission in submissions:
        record = reviews[submission]
        scores_str_list = [
            f'{sc:.1f}' if sc != '?' else '?' for sc in record['scores_list']]
        try:
            document.add_heading(
                f'#{submission.pk}: {submission.title}', level=1)
        except ValueError:
            document.add_heading(
                f'#{submission.pk}: [title hidden due to illegal characters]',
                level=1)

        p = document.add_paragraph()
        p.add_run('Review Score: ').bold = True
        p.add_run(f'{record["score"]:.2f} ({record["quality"]}, scores: '
                  f'{"/".join(scores_str_list)})')
        p = document.add_paragraph()
        p.add_run('Reviews finished / assigned / required: ').bold = True
        p.add_run(f"{record['num_finished']} / {record['num_assigned']} / "
                  f"{record['num_required']}")
        p = document.add_paragraph()
        p.add_run('Authors: ').bold = True
        authors = submission.authors.all()
        for i, author in enumerate(authors):
            profile = profiles[author.user]
            p = document.add_paragraph(f'{i + 1}. ')
            p.add_run(profile.get_full_name()).bold = True
            name_rus = f'{profile.first_name_rus} {profile.last_name_rus}'
            if name_rus != ' ':
                p.add_run(f' [{name_rus}]')
            p.add_run(' (')
            p.add_run(
                f'{profile.get_country_display()}, {profile.affiliation}, '
                f'{profile.degree}').italic = True
            p.add_run(')')
        # p = document.add_paragraph()
        # p.add_run('Abstract:').bold = True
        # document.add_paragraph(submission.abstract)
        for i, review in enumerate(submission.reviews.all()):
            reviewer_profile = profiles[review.reviewer.user]
            document.add_heading(
                f'Review #{i+1} by {reviewer_profile.get_full_name()}',
                level=2)
            review_data = (
                ('Technical merit', review.technical_merit),
                ('Originality', review.originality),
                ('Relevance', review.relevance),
                ('Clarity', review.clarity),
                ('Finished', 'Yes' if review.submitted else 'No'),
            )
            table = document.add_table(rows=len(review_data), cols=2)
            for row_i, row in enumerate(review_data):
                table.rows[row_i].cells[0].text = row[0]
                table.rows[row_i].cells[1].text = row[1]
            for row in table.rows:
                row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
                row.height = Cm(0.7)
            try:
                document.add_paragraph(review.details)
            except ValueError:
                p = document.add_paragraph()
                p.add_run('[Review details hidden since they contain illegal '
                          'characters and can not be processed in .docx '
                          'format]').italic = True

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.'
                     'wordprocessingml.document')
    response['Content-Disposition'] = \
        f'attachment; filename=reviews-{timestamp}.docx'
    document.save(response)

    return response

