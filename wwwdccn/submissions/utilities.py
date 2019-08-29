from django.utils import timezone


def camera_editable(submission):
    decision = submission.review_decision.first()
    proc_type = getattr(decision, 'proc_type', None)
    end_date = getattr(proc_type, 'final_manuscript_deadline', None)
    too_late = end_date and timezone.now() > end_date
    return submission.status == submission.ACCEPTED and not too_late


def is_authorized_edit(user, submission):
    return submission.is_author(user) or submission.is_chaired_by(user)


def is_authorized_view_artifact(user, submission):
    return submission.is_author(user) or submission.is_chaired_by(user)
