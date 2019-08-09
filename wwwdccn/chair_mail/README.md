Messaging subsystem
===================

## Message composing

Messaging subsystem provides means for composing messages to groups of users. Message is written in Markdown syntax. 
Depending on the message target (list of users, authors of given submissions, etc.) different template variables
can be used.

There are three difference views for message composing:

1. Composing to a particular user
2. Composing to a particular submission authors
3. Composing to a selectable user list

The most difficult part is the message previewing: it is merely impossible to provide chair with separate values
settings (like, e.g., in Mailgun), but rather it is preferable to select model objects (users, submissions, etc.) for
preview. However, the list of objects (and even a set of their types) depends on the target. For instance, we may
select a list of incomplete submissions and write to their authors, and then decide that we write a message to
authors who simply have at least one incomplete submission. In the first case, in the preview window submission
selection should be available, while in the second only user selection should.

Moreover, a set of possible values also depends on the selected destination: only one user is meaningful when
composing to a given user, single submission and all its authors - when composing to a given submission. And when
composing to a selectable user list, possible values change when we change the value of the destination.

