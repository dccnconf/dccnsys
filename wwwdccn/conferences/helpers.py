def can_edit_conference(user, conference):
    return user in conference.chairs.all()


def get_authors_of(submissions):
    """Get a set of unique users those are authors of the given submissions.

    :param submissions: List[Submission]
    :return:
    """
    all_authors = []
    for submission in submissions:
        all_authors.extend(submission.authors.all())
    all_users = [author.user for author in all_authors]
    return set(all_users)
