def get_countries_of(submission):
    authors = list(submission.authors.all())
    profiles = [author.user.profile for author in authors]
    countries = [profile.country for profile in profiles]
    return list(set(countries))


def get_affiliations_of(submission):
    authors = list(submission.authors.all())
    profiles = [author.user.profile for author in authors]
    affiliations = [profile.affiliation for profile in profiles]
    return list(set(affiliations))
