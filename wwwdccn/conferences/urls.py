from django.urls import path

from . import views


app_name = 'conferences'
urlpatterns = [
    path('ajax/<int:pk>/', views.ajax_details),
    path('ajax/stype/<int:pk>/', views.ajax_stype_details),

    path('', views.conferences_list,
         name='list'),
    path('new/', views.conference_create, name='create'),
    path('<int:pk>/', views.conference_details, name='details'),
    path('<int:pk>/settings/', views.conference_edit, name='edit'),
    path('<int:pk>/stages/submission', views.conference_submission_stage,
         name='submission-deadline'),
    path('<int:pk>/stages/reviews', views.conference_review_stage,
         name='review-deadline'),
    path('<int:pk>/proceedings/new/', views.proceedings_create,
         name='proceedings-create'),
    path('<int:pk>/proceedings/<int:proc_pk>/', views.proceedings_update,
         name='proceedings-update'),
    path('<int:pk>/proceedings/<int:proc_pk>/delete/', views.proceedings_delete,
         name='proceedings-delete'),
    path('<int:pk>/stype/new/', views.submission_type_create,
         name='stype-create'),
    path('<int:pk>/stype/<int:sub_pk>/', views.submission_type_update,
         name='stype-update'),
    path('<int:pk>/stype/<int:sub_pk>/delete/', views.submission_type_delete,
         name='stype-delete'),
    path('<int:pk>/topics/', views.topics_list, name='topics'),
    path('<int:pk>/topics/<int:topic_pk>/delete/', views.topic_delete,
         name='topic-delete'),
    path('<int:pk>/topics/<int:topic_pk>/', views.topic_update,
         name='topic-update'),
    path('<int:pk>/topics/reorder/', views.topics_reorder,
         name='topics-reorder'),
]
