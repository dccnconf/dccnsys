def count_required_reviews(submission, cached_stypes=None):
    """Return the number of required reviews for the submission.
    If `cached_stypes` provided, it should contain a `stype.pk -> stype`
    mapping.

    :param submission: `Submission` instance
    :param cached_stypes: optional mapping `stype.pk -> stype`
    :return: number of reviews required for the submission
    """
    if submission.stype:
        stype_pk = submission.stype_id
        if cached_stypes and stype_pk in cached_stypes:
            return cached_stypes[stype_pk].num_reviews
        return submission.stype.num_reviews
    return 0


def review_finished(submission, cached_stypes=None):
    """Check whether the number of submitted reviews is equal to the number
    of required reviews.

    :param submission: `Submission` instance
    :param cached_stypes: optional mapping `stype.pk -> stype`
    :return `True` if the number of submitted reviews is equal to the required
    """
    return (submission.reviews.filter(submitted=True).count() ==
            count_required_reviews(submission, cached_stypes))


def get_average_score(obj):
    """Estimate average score of a given object. The object may be a `Review` or
    `Submission` instance, as well as an iterable of other objects.

    > NOTE: if the object is a `Submission` instance or an iterable,
    > only reviews/items with correctly estimated score will be taken into
    > account. The "correct score" is the score greater then zero, since
    > `Review.average_score()` method returns 0 if `Review` is not complete.

    :return: average score or `0` if score can not be estimated.
    """
    try:
        # If obj is a Review instance, just use its model method:
        return obj.average_score()
    except AttributeError:
        try:
            # If obj is not a Review, assume that it is Submission:
            scores = [get_average_score(rev) for rev in obj.reviews.all()]
        except AttributeError:
            # If obj is not Review or Submission, assume it is
            # a collection of either objects:
            scores = [get_average_score(item) for item in obj]
        # Finally, filter correct scores (which must be greater then zero)
        # and estimate average score on the scores of parts
        scores = [score for score in scores if score > 0]
        return sum(scores) / len(scores) if scores else 0.0
