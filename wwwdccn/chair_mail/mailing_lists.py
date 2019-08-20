from collections import namedtuple

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from chair_mail.models import MSG_TYPE_USER, MSG_TYPE_SUBMISSION
from review.models import Reviewer
from submissions.models import Author, Submission
from users.models import User

ml = namedtuple('MailingList', ('name', 'details', 'type', 'query'))


ALL_USERS = ml(
    'ALL_USERS', _('All users'), MSG_TYPE_USER,
    lambda conference: User.objects.all(),
)

ALL_AUTHORS = ml(
    'ALL_AUTHORS', _('All users with at least one submission'),
    MSG_TYPE_USER,
    lambda conference: User.objects.filter(authorship__in=Author.objects.filter(
        submission__conference=conference
    )).distinct()
)

USERS_WITH_MISSING_MANUSCRIPT = ml(
    'USERS_WITH_MISSING_MANUSCRIPT',
    _('Users with at least one submission missing review manuscript'),
    MSG_TYPE_USER,
    lambda conference: User.objects.filter(authorship__in=Author.objects.filter(
        Q(submission__conference=conference) &
        Q(submission__review_manuscript='')
    )).distinct()
)

USERS_WITH_EMPTY_SUBMISSION = ml(
    'USERS_WITH_EMPTY_SUBMISSIONS',
    _('Users with at least one empty submission'),
    MSG_TYPE_USER,
    lambda conference: User.objects.filter(authorship__in=Author.objects.filter(
        Q(submission__conference=conference) & Q(submission__title='')
    )).distinct()
)

ALL_REVIEWERS = ml(
    'ALL_REVIEWERS', _('All reviewers'), MSG_TYPE_USER,
    lambda conference: User.objects.filter(
        reviewer__conference=conference
    ))

REVIEWERS_WITH_INCOMPLETE_REVIEWS = ml(
    'REVIEWERS_WITH_INCOMPLETE_REVIEWS',
    _('Reviewers with at least on incomplete review'),
    MSG_TYPE_USER,
    lambda conference: User.objects.filter(reviewer__in=Reviewer.objects.filter(
        reviews__submitted=False
    ))
)

ALL_SUBMISSIONS = ml(
    'ALL_SUBMISSIONS', _('All submissions'), MSG_TYPE_SUBMISSION,
    lambda conference: Submission.objects.filter(conference=conference)
)

INCOMPLETE_SUBMISSIONS = ml(
    'SUBMISSIONS_MISSING_REVIEW_MANUSCRIPT',
    _('Submissions missing review manuscript'),
    MSG_TYPE_SUBMISSION,
    lambda conference: Submission.objects.filter(
        Q(conference=conference) & Q(review_manuscript='')
    ).exclude(title='')
)

EMPTY_SUBMISSIONS = ml(
    'EMPTY_SUBMISSIONS', _('Empty submissions'), MSG_TYPE_SUBMISSION,
    lambda conference: Submission.objects.filter(
        Q(conference=conference) & Q(title='')
    )
)

USER_LISTS = (
    ALL_USERS,
    ALL_AUTHORS,
    USERS_WITH_MISSING_MANUSCRIPT,
    USERS_WITH_EMPTY_SUBMISSION,
    ALL_REVIEWERS,
    REVIEWERS_WITH_INCOMPLETE_REVIEWS,
)

SUBMISSION_LISTS = (
    ALL_SUBMISSIONS,
    INCOMPLETE_SUBMISSIONS,
    EMPTY_SUBMISSIONS,
)

ALL_LISTS = USER_LISTS + SUBMISSION_LISTS


def find_list(list_name):
    try:
        return [a_list for a_list in ALL_LISTS if a_list.name == list_name][0]
    except IndexError:
        raise KeyError(f'invalid mailing list {list_name}')


def get_users_of(mailing_list, conference):
    if mailing_list.type == MSG_TYPE_USER:
        return mailing_list.query(conference)
    elif mailing_list.type == MSG_TYPE_SUBMISSION:
        submissions = mailing_list.query(conference)
        authors = Author.objects.filter(submission__in=submissions).distinct()
        return User.objects.filter(authorship__in=authors).distinct()
    else:
        assert False
