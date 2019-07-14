from django.urls import path

from . import views


app_name = 'chair'

urlpatterns = [
    path('<int:pk>/', views.dashboard, name='home'),

    #
    # Submissions listing
    #
    path('<int:pk>/submissions/', views.submissions_list, name='submissions'),
    path('<int:pk>/submissions/pages/<int:page>/', views.submissions_list, name='submissions-pages'),

    #
    # Submission views and actions
    #
    path('submission/<int:pk>/overview/', views.submission_overview, name='submission-overview'),
    path('submission/<int:pk>/metadata/', views.submission_metadata, name='submission-metadata'),
    path('submission/<int:pk>/authors/', views.submission_authors, name='submission-authors'),
    path('submission/<int:pk>/authors/delete/', views.submission_author_delete, name='submission-author-delete'),
    path('submission/<int:pk>/authors/create/', views.submission_author_create, name='submission-author-create'),
    path('submission/<int:pk>/authors/invite/', views.submission_author_invite, name='submission-author-invite'),
    path('submission/<int:pk>/authors/reorder/', views.submission_authors_reorder, name='submission-authors-reorder'),
    path('submission/<int:pk>/review_manuscript/', views.submission_review_manuscript, name='submission-review-manuscript'),
    path('submission/<int:pk>/review_manuscript/delete/', views.submission_delete_review_manuscript, name='submission-review-manuscript-delete'),
    path('submission/<int:pk>/start_review/', views.start_review, name='start-review'),
    path('submission/<int:pk>/revoke_review/', views.revoke_review, name='revoke-review'),
    path('submission/<int:pk>/reviewers/', views.submission_reviewers, name='submission-reviewers'),
    path('submission/<int:pk>/reviewers/assign/', views.assign_reviewer, name='assign-reviewer'),

    #
    # Users listing
    #
    path('<int:pk>/users/', views.users_list, name='users'),
    path('<int:pk>/users/pages/<int:page>/', views.users_list,name='users-pages'),

    path('<int:pk>/users/<int:user_pk>', views.user_details, name='user'),

    path('<int:pk>/reviewers/', views.reviewers_list, name='reviewers'),
    path('<int:pk>/reviewers/pages/<int:page>/', views.reviewers_list, name='reviewers-pages'),
    path('<int:conf_pk>/reviewers/invite/<int:user_pk>/', views.invite_reviewer, name='invite-reviewer'),
    path('<int:conf_pk>/reviewers/revoke/<int:user_pk>/', views.revoke_reviewer, name='revoke-reviewer'),

    path('<int:pk>/export/submissions/', views.get_submissions_csv, name='export-submissions-csv'),
    path('<int:pk>/export/authors/', views.get_authors_csv, name='export-authors-csv'),

    # AJAX PARTIAL HTML PIECES:
    path('ajax_html/submissions/<int:pk>/overview/', views.get_submission_overview, name='get-submission-overview'),
]
