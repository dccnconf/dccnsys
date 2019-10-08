from review.models import ReviewDecisionType


def get_allowed_decision_types(submission, decision):
    conference_id = submission.conference_id
    if decision == ReviewDecisionType.REJECT:
        return ReviewDecisionType.objects.filter(
            decision=decision, conference=conference_id)

    if submission.stype_id is None:
        return ReviewDecisionType.objects.filter(id__isnull=True)

    return ReviewDecisionType.objects.filter(
        decision=decision,
        conference=conference_id,
        allowed_proceedings__in=submission.stype.possible_proceedings.all()
    ).distinct()
