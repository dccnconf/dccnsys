def can_edit_conference(user, conference):
    return user in conference.chairs.all()
