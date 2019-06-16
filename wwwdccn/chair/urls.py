from django.urls import path

from . import views


app_name = 'chair'

urlpatterns = [
    path('<int:pk>/', views.dashboard, name='home'),

    path('<int:pk>/submissions/', views.submissions_list, name='submissions'),
    path('<int:pk>/submissions/pages/<int:page>/', views.submissions_list,
         name='submissions-pages'),

    path('<int:pk>/users/', views.users_list, name='users'),
    path('<int:pk>/users/pages/<int:page>/', views.users_list,
         name='users-pages'),

    path('<int:pk>/users/<int:user_pk>', views.user_details, name='user'),

    path('<int:pk>/export/submissions/', views.get_submissions_csv,
         name='export-submissions-csv'),
    path('<int:pk>/export/authors/', views.get_authors_csv,
         name='export-authors-csv'),

    # AJAX PARTIAL HTML PIECES:
    path('ajax_html/submissions/<int:pk>/overview/',
         views.get_submission_overview, name='get-submission-overview'),
]
