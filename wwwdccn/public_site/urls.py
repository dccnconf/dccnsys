from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='public_site/index.html'), name='public_index'),
    path('', TemplateView.as_view(template_name='public_site/index.html'), name='home'),
]
