from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from collections import namedtuple

from chair_mail.utility import get_absolute_url, markdownify_link, \
    markdownify_list
from review.models import Review
from submissions.models import Submission

Var = namedtuple('Var', ('name', 'description'))


#
# FRAME CONTEXT (DO NOT USE IT IN GROUP MESSAGE RENDERING!!!)
#
FRAME_SUBJECT = Var('subject', _('subject defined when writing a new letter'))
FRAME_BODY = Var('body', _('body of the letter'))
FRAME_SITE_URL = Var('site_url', _('link to the registration system site'))
FRAME_CONF_EMAIL = Var('conf_email', _('email for contacting organizers'))
FRAME_CONF_SITE_URL = Var('conf_site_url', _('URL of the conference web site'))
FRAME_CONF_FULL_NAME = Var('conf_full_name', _('full name of the conference'))
FRAME_CONF_SHORT_NAME = Var('conf_short_name', _('short name of the conference'))
FRAME_CONF_LOGO_URL = Var(
    'conf_logo_url',
    _('URL of the conference logotype. Note, that it better should be located '
      'at some well-known source (like Google Drive or Amazon S3), since some '
      'email clients may cut images from suspicious sources.'))

FRAME_VARS = tuple((var.name, var.description) for var in (
    FRAME_SUBJECT, FRAME_BODY, FRAME_SITE_URL, FRAME_CONF_EMAIL,
    FRAME_CONF_SITE_URL, FRAME_CONF_FULL_NAME, FRAME_CONF_SHORT_NAME,
    FRAME_CONF_LOGO_URL
))


def get_frame_context(conference, subject, body):
    """Build frame context. It differs from GroupMessage rendering since
    frame is separately defined in HTML and plain-text: we don't need
    to enclose references in Markdown or HTML.
    """
    return {
        FRAME_SUBJECT.name: subject,
        FRAME_BODY.name: body,
        FRAME_SITE_URL.name:
            f'{settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}',
        FRAME_CONF_EMAIL.name: conference.contact_email,
        FRAME_CONF_SITE_URL.name: conference.site_url,
        FRAME_CONF_FULL_NAME.name: conference.full_name,
        FRAME_CONF_SHORT_NAME.name: conference.short_name,
        FRAME_CONF_LOGO_URL.name:
            conference.logotype.url if conference.logotype else ''
    }


#
# CONFERENCE CONTEXT
#
CONF_SHORT_NAME = Var('conf_short_name', _('short name of the conference'))
CONF_FULL_NAME = Var('conf_full_name', _('full name of the conference'))
CONF_START_DATE = Var('conf_start_date', _('conference start date'))
CONF_END_DATE = Var('conf_end_date', _('conference end date'))
CONF_SITE_URL = Var('conf_site_url', _('conference site URL'))
CONF_EMAIL = Var('conf_email', _('email of the organizing committee'))
SUBMISSION_END_DATETIME = Var('sub_end_date', _('end of submission datetime'))
REVIEW_END_DATETIME = Var('rev_end_date', _('end of review datetime'))

CONFERENCE_VARS = tuple((var.name, var.description) for var in (
    CONF_SHORT_NAME, CONF_FULL_NAME, CONF_START_DATE, CONF_END_DATE,
    CONF_SITE_URL, CONF_EMAIL, SUBMISSION_END_DATETIME, REVIEW_END_DATETIME,
))


def get_conference_context(conference):
    return {
        CONF_SHORT_NAME.name: conference.short_name,
        CONF_FULL_NAME.name: conference.full_name,
        CONF_START_DATE.name: conference.start_date,
        CONF_END_DATE.name: conference.close_date,
        CONF_SITE_URL.name: markdownify_link(conference.site_url),
        CONF_EMAIL.name: markdownify_link(conference.contact_email, 'mailto:'),
        SUBMISSION_END_DATETIME.name: conference.submission_stage.end_date,
        REVIEW_END_DATETIME.name: conference.review_stage.end_date,
    }


#
# USER CONTEXT
#
# - user profile context:
#
USERNAME = Var('username', _('user full name in English'))
FIRST_NAME = Var('first_name', _('user first name in English'))
LAST_NAME = Var('last_name', _('user last name in English'))
USER_ID = Var('user_id', _('user ID'))

USER_PROFILE_VARS = tuple((var.name, var.description) for var in (
    USERNAME, FIRST_NAME, LAST_NAME, USER_ID
))


def _get_user_profile_context(user):
    """Get context dictionary regarding user profile.
    """
    profile = user.profile
    return {
        USERNAME.name: profile.get_full_name(),
        FIRST_NAME.name: profile.first_name,
        LAST_NAME.name: profile.last_name,
        USER_ID.name: user.pk
    }


#
# - user submissions context:
#
NUM_PAPERS = Var('num_papers',  _('number of papers authored by the user'))
PAPERS_LIST = Var('papers_list', _('list of all papers authored by the user'))
NUM_SUBMITTED_PAPERS = Var(
    'num_submitted_papers',
    _('number of papers in "submitted" phase')
)
SUBMITTED_PAPERS_LIST = Var(
    'submitted_papers_list',
    _('list of all papers in "submitted" phase')
)
NUM_INCOMPLETE_SUBMITTED_PAPERS = Var(
    'num_incomplete_submitted_papers',
    _('number of partially filled papers in "submitted" phase')
)
INCOMPLETE_SUBMITTED_PAPERS_LIST = Var(
    'incomplete_submitted_papers_list',
    _('list of partially filled papers in "submitted" phase')
)
NUM_COMPLETE_SUBMITTED_PAPERS = Var(
    'num_complete_submitted_papers',
    _('number of completely filled papers in "submitted" phase')
)
COMPLETE_SUBMITTED_PAPERS_LIST = Var(
    'complete_submitted_papers_list',
    _('list of completely filled papers in "submitted" phase'))
NUM_EMPTY_PAPERS = Var(
    'num_empty_papers',
    _('number of papers without even title')
)
EMPTY_PAPERS_LIST = Var(
    'empty_papers_list',
    _('list of papers without even title')
)
NUM_UNDER_REVIEW_PAPERS = Var(
    'num_under_review_papers',
    _('number of papers authored by the user being under review')
)
UNDER_REVIEW_PAPERS_LIST = Var(
    'under_review_papers_list',
    _('list of papers authored by the user being under review')
)

USER_SUBMISSIONS_VARS = tuple((var.name, var.description) for var in (
    NUM_PAPERS, PAPERS_LIST, NUM_SUBMITTED_PAPERS, SUBMITTED_PAPERS_LIST,
    NUM_INCOMPLETE_SUBMITTED_PAPERS, INCOMPLETE_SUBMITTED_PAPERS_LIST,
    NUM_COMPLETE_SUBMITTED_PAPERS, COMPLETE_SUBMITTED_PAPERS_LIST,
    NUM_EMPTY_PAPERS, EMPTY_PAPERS_LIST,
    NUM_UNDER_REVIEW_PAPERS, UNDER_REVIEW_PAPERS_LIST,
))


def _get_user_submissions_context(user, conference):
    """Get context dictionary regarding user submissions.
    """
    # TODO: add context for accepted and rejected papers
    papers = (Submission.objects
              .filter(conference=conference)
              .filter(authors__user=user))
    complete_ids = [p.pk for p in papers if not p.warnings()]
    _submitted = papers.filter(status=Submission.SUBMITTED)
    under_review = papers.filter(status=Submission.UNDER_REVIEW)
    submitted = {
        'all': _submitted,
        'complete': _submitted.filter(pk__in=complete_ids),
        'incomplete': _submitted.exclude(pk__in=complete_ids),
        'empty': _submitted.filter(title='')
    }

    # Helper to build markdown representation of the queryset:
    def get_displayed_title(submission):
        title = submission.title
        if not title:
            return f'*no title*'
        return f'{title}'

    def ul(query, default_value=''):
        return markdownify_list(
            query,
            get_item_value=get_displayed_title,
            get_item_url=lambda sub: get_absolute_url(
                reverse('submissions:overview', kwargs={'pk': sub.pk})),
            default_value='no name',
        )

    return {
        NUM_PAPERS.name: papers.count(),
        PAPERS_LIST.name: ul(papers),
        NUM_SUBMITTED_PAPERS.name: submitted['all'].count(),
        SUBMITTED_PAPERS_LIST.name: ul(submitted['all']),
        NUM_COMPLETE_SUBMITTED_PAPERS.name: submitted['complete'].count(),
        COMPLETE_SUBMITTED_PAPERS_LIST.name:ul(submitted['complete']),
        NUM_INCOMPLETE_SUBMITTED_PAPERS.name: submitted['incomplete'].count(),
        INCOMPLETE_SUBMITTED_PAPERS_LIST.name: ul(submitted['incomplete']),
        NUM_EMPTY_PAPERS.name: submitted['empty'].count(),
        EMPTY_PAPERS_LIST.name: ul(submitted['empty']),
        NUM_UNDER_REVIEW_PAPERS.name: under_review.count(),
        UNDER_REVIEW_PAPERS_LIST.name: ul(under_review)
    }


#
# - user reviews context:
#
NUM_REVIEWS = Var('num_reviews', _('number of reviews assigned to this user'))
REVIEWS_LIST = Var('reviews_list', _('list of reviews assigned to this user'))
NUM_COMPLETE_REVIEWS = Var(
    'num_complete_reviews',
    _('number of completed reviews assigned to this user')
)
COMPLETE_REVIEWS_LIST = Var(
    'complete_reviews_list',
    _('list of completed reviews assigned to this user'),
)
NUM_INCOMPLETE_REVIEWS = Var(
    'num_incomplete_reviews',
    _('number of reviews to be finished'),
)
INCOMPLETE_REVIEWS_LIST = Var(
    'incomplete_reviews_list',
    _('list of reviews to be finished')
)

USER_REVIEWS_VARS = tuple((var.name, var.description) for var in (
    NUM_REVIEWS, REVIEWS_LIST, NUM_COMPLETE_REVIEWS, COMPLETE_REVIEWS_LIST,
    NUM_INCOMPLETE_REVIEWS, INCOMPLETE_REVIEWS_LIST
))


def _get_user_review_context(user, conference):
    """Get context dictionary regarding user reviews.
    """
    reviews = (Review.objects
               .filter(paper__conference=conference)
               .filter(reviewer__user=user))
    complete_reviews_ids = [rev.pk for rev in reviews if not rev.warnings()]
    complete_reviews = reviews.filter(pk__in=complete_reviews_ids)
    incomplete_reviews = reviews.exclude(pk__in=complete_reviews_ids)

    # Helper to build <ul>-representation of the queryset:
    def ul(query):
        return markdownify_list(
            query,
            get_item_value=lambda rev: rev.paper.title,
            get_item_url=lambda rev: get_absolute_url(
                reverse('review:review-details', kwargs={'pk': rev.pk}))
        )

    return {
        NUM_REVIEWS.name: reviews.count(),
        REVIEWS_LIST.name: ul(reviews),
        NUM_COMPLETE_REVIEWS.name: complete_reviews.count(),
        COMPLETE_REVIEWS_LIST.name: ul(complete_reviews),
        NUM_INCOMPLETE_REVIEWS.name: incomplete_reviews.count(),
        INCOMPLETE_REVIEWS_LIST.name: ul(incomplete_reviews),
    }


#
# ---- BUILDING USER CONTEXT AND VARS ----
#
def get_user_context(user, conference):
    return {
        **_get_user_profile_context(user),
        **_get_user_submissions_context(user, conference),
        **_get_user_review_context(user, conference),
    }


USER_VARS = USER_PROFILE_VARS + USER_SUBMISSIONS_VARS + USER_REVIEWS_VARS


#
# SUBMISSION CONTEXT
#
SUB_ID = Var('paper_id', _('submission ID'))
SUB_TITLE = Var('paper_title', _('paper title'))
SUB_ABSTRACT = Var('paper_abstract', _('paper abstract'))
SUB_AUTHORS = Var('paper_authors', _('paper authors string'))
SUB_URL = Var('paper_url', _('URL of the paper'))
# TODO: add variables for review results


SUBMISSION_VARS = tuple((var.name, var.description) for var in (
    SUB_ID, SUB_TITLE, SUB_ABSTRACT, SUB_AUTHORS, SUB_URL,
))


def get_submission_context(submission):
    return {
        SUB_ID.name: submission.pk,
        SUB_TITLE.name: submission.title,
        SUB_ABSTRACT.name: submission.abstract,
        SUB_AUTHORS.name: submission.get_authors_display(),
        SUB_URL.name: markdownify_link(get_absolute_url(
            reverse('submissions:overview', kwargs={'pk': submission.pk}))),
    }
