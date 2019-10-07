from review.models import ReviewDecisionType


def get_allowed_decision_types(submission, decision):
    if decision == ReviewDecisionType.REJECT:
        return ReviewDecisionType.objects.filter(decision=decision)

    if submission.stype_id is None:
        return ReviewDecisionType.objects.filter(id__isnull=True)

    return ReviewDecisionType.objects.filter(
        decision=decision,
        allowed_proceedings__in=submission.stype.possible_proceedings.all()).distinct()
