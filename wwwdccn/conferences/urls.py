from django.urls import path

from . import views


urlpatterns = [
    path('ajax/<int:pk>/', views.ajax_conference_details,
         name='ajax-conference-details'),
    path('ajax/stype/<int:pk>/', views.ajax_submission_type_details,
         name='ajax-submission-type-details'),

    path('/', views.conferences_list,
         name='conferences-list'),
    path('new/', views.conference_create, name='conference-create'),
    path('<int:pk>/', views.conference_details, name='conference-details'),
    path('<int:pk>/settings/', views.conference_edit, name='conference-edit'),
    path('<int:pk>/stages/submission', views.conference_submission_stage,
         name='conference-submission-stage'),
    path('<int:pk>/stages/reviews', views.conference_review_stage,
         name='conference-review-stage'),
    path('<int:pk>/proceedings/new/', views.proceedings_create,
         name='conference-proceedings-create'),
    path('<int:pk>/proceedings/<int:proc_pk>/', views.proceedings_update,
         name='conference-proceedings-update'),
    path('<int:pk>/proceedings/<int:proc_pk>/delete/', views.proceedings_delete,
         name='conference-proceedings-delete'),
    path('<int:pk>/stype/new/', views.submission_type_create,
         name='conference-submissiontype-create'),
    path('<int:pk>/stype/<int:sub_pk>/', views.submission_type_update,
         name='conference-submissiontype-update'),
    path('<int:pk>/stype/<int:sub_pk>/delete/', views.submission_type_delete,
         name='conference-submissiontype-delete'),
    path('<int:pk>/topics/', views.topics_list, name='conference-topics'),
    path('<int:pk>/topics/<int:topic_pk>/delete/', views.topic_delete,
         name='conference-topic-delete'),
    path('<int:pk>/topics/<int:topic_pk>/', views.topic_update,
         name='conference-topic-update'),
    path('<int:pk>/topics/reorder/', views.topics_reorder,
         name='conference-topics-reorder'),
]
