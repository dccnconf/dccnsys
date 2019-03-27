from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='register-personal'),
         name='register'),
    path('personal/', views.personal, name='register-personal'),
    path('professional/', views.professional, name='register-professional'),
    path('subscriptions/', views.subscriptions, name='register-subscriptions'),
]
