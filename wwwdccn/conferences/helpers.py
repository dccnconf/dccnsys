from submissions import helpers as submissions_helpers


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


def get_countries_of(submissions):
    lists = [submissions_helpers.get_countries_of(submission)
             for submission in submissions]
    countries_set = set()
    for countries_list in lists:
        for country in countries_list:
            countries_set.add(country)
    ret = list(countries_set)
    return sorted(ret, key=lambda cnt: cnt.name)


def get_affiliations_of(submissions):
    lists = [submissions_helpers.get_affiliations_of(submission)
             for submission in submissions]
    ret_set = set()
    for _list in lists:
        for item in _list:
            ret_set.add(item)
    ret = list(ret_set)
    return sorted(ret)
