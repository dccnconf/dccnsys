from django.urls import path

from .views import dashboard, submissions, users, reviews


app_name = 'chair'

urlpatterns = [
    path('<int:conf_pk>/', dashboard.overview, name='home'),

    #
    # Submissions
    #
    path('<int:conf_pk>/submissions/', submissions.list_submissions, name='submissions'),
    path('<int:conf_pk>/submissions/pages/<int:page>/', submissions.list_submissions, name='submissions-pages'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/overview/', submissions.overview, name='submission-overview'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/metadata/', submissions.metadata, name='submission-metadata'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/authors/', submissions.authors, name='submission-authors'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/authors/delete/', submissions.delete_author, name='submission-author-delete'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/authors/create/', submissions.create_author, name='submission-author-create'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/authors/invite/', submissions.invite_author, name='submission-author-invite'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/authors/reorder/', submissions.reorder_authors, name='submission-authors-reorder'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/rev_man/', submissions.review_manuscript, name='submission-review-manuscript'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/rev_man/delete/', submissions.delete_review_manuscript, name='submission-review-manuscript-delete'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/start_review/', submissions.start_review, name='start-review'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/revoke_review/', submissions.revoke_review, name='revoke-review'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/reviews/', submissions.reviews, name='submission-reviewers'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/messages/', submissions.emails, name='submission-messages'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/reviews/assign/', submissions.assign_reviewer, name='assign-reviewer'),
    path('<int:conf_pk>/submissions/<int:sub_pk>/reviews/<int:rev_pk>/delete/', submissions.delete_review, name='delete-review'),
    path('<int:conf_pk>/submissions/export/csv/', submissions.export_csv, name='export-submissions-csv'),

    #
    # Users
    #
    path('<int:conf_pk>/users/', users.list_users, name='users'),
    path('<int:conf_pk>/users/pages/<int:page>/', users.list_users, name='users-pages'),
    path('<int:conf_pk>/users/<int:user_pk>/overview/', users.overview, name='user-overview'),
    path('<int:conf_pk>/users/<int:user_pk>/messages/', users.emails, name='user-messages'),
    path('<int:conf_pk>/reviewers/invite/<int:user_pk>/', users.create_reviewer, name='invite-reviewer'),
    path('<int:conf_pk>/reviewers/revoke/<int:user_pk>/', users.revoke_reviewer, name='revoke-reviewer'),
    path('<int:conf_pk>/authors/export/csv/', users.export_csv, name='export-authors-csv'),

    #
    # Reviews
    #
    path('<int:conf_pk>/reviews/', reviews.list_submissions, name='reviews'),
    path('<int:conf_pk>/reviews/pages/<int:page>/', reviews.list_submissions, name='reviews-pages'),
    path('<int:conf_pk>/reviews/export/docx/', reviews.export_doc, name='export-reviews-doc'),
    path('<int:conf_pk>/reviews/<int:sub_pk>/decision_control_panel/', reviews.decision_control_panel, name='review-decision-control'),
    path('<int:conf_pk>/reviews/<int:sub_pk>/commit_decision/', reviews.commit_decision, name='review-decision-commit'),
]
