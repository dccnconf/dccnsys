from django.urls import path

from chair.views import export
from .views import dashboard, submissions, users


app_name = 'chair'

urlpatterns = [
    path('<int:conf_pk>/', dashboard.overview, name='home'),

    #
    # Submissions
    #
    path('<int:conf_pk>/submissions/', submissions.list_submissions, name='submissions'),
    path('<int:conf_pk>/submissions/create/', submissions.create_submission, name='submission-create'),
    path('submissions/<int:sub_pk>/feed_item/', submissions.feed_item, name='submission-feed-item'),
    path('submissions/<int:sub_pk>/overview/', submissions.overview, name='submission-overview'),
    path('submissions/<int:sub_pk>/metadata/', submissions.metadata, name='submission-metadata'),
    path('submissions/<int:sub_pk>/authors/', submissions.authors, name='submission-authors'),
    path('submissions/<int:sub_pk>/authors/delete/', submissions.delete_author, name='submission-author-delete'),
    path('submissions/<int:sub_pk>/authors/create/', submissions.create_author, name='submission-author-create'),
    path('submissions/<int:sub_pk>/authors/invite/', submissions.invite_author, name='submission-author-invite'),
    path('submissions/<int:sub_pk>/authors/reorder/', submissions.reorder_authors, name='submission-authors-reorder'),
    path('submissions/<int:sub_pk>/rev_man/', submissions.review_manuscript, name='submission-review-manuscript'),
    path('submissions/<int:sub_pk>/rev_man/delete/', submissions.delete_review_manuscript, name='submission-review-manuscript-delete'),
    path('submissions/<int:sub_pk>/start_review/', submissions.start_review, name='start-review'),
    path('submissions/<int:sub_pk>/revoke_review/', submissions.revoke_review, name='revoke-review'),
    path('submissions/<int:sub_pk>/reviews/', submissions.reviews, name='submission-reviewers'),
    path('submissions/<int:sub_pk>/messages/', submissions.emails, name='submission-messages'),
    path('submissions/<int:sub_pk>/reviews/assign/', submissions.assign_reviewer, name='assign-reviewer'),
    path('submissions/<int:sub_pk>/reviews/<int:rev_pk>/delete/', submissions.delete_review, name='delete-review'),
    path('submissions/<int:sub_pk>/delete/', submissions.delete_submission, name='submission-delete'),
    path('artifacts/<int:art_pk>/download/', submissions.artifact_download, name='artifact-download'),

    #
    # Users
    #
    path('<int:conf_pk>/users/', users.list_users, name='users'),
    path('<int:conf_pk>/users/<int:user_pk>/overview/', users.overview, name='user-overview'),
    path('<int:conf_pk>/users/<int:user_pk>/messages/', users.emails, name='user-messages'),
    path('<int:conf_pk>/reviewers/invite/<int:user_pk>/', users.create_reviewer, name='invite-reviewer'),
    path('<int:conf_pk>/reviewers/revoke/<int:user_pk>/', users.revoke_reviewer, name='revoke-reviewer'),

    #
    # Exports
    #
    path('<int:conf_pk>/export/submissions/', export.export_submissions, name='export-submissions'),
    path('<int:conf_pk>/export/users/', export.export_users, name='export-users'),
]
