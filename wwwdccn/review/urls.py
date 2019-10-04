from django.urls import path

from . import views


app_name = 'review'

urlpatterns = [
    path('<int:pk>/', views.review_details, name='review-details'),
    path('<int:pk>/refuse/', views.decline_review, name='review-decline'),
    # API:
    path('api/decision/<int:sub_pk>/', views.update_decision, name='update-decision'),
    path('api/<int:conf_pk>/users/<int:user_pk>/make_reviewer/', views.create_reviewer, name='make-reviewer'),
    path('api/<int:conf_pk>/users/<int:user_pk>/revoke_reviewer/', views.revoke_reviewer, name='revoke-reviewer'),
]
