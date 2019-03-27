from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404

User = get_user_model()

# Create your views here.
def user_details(request):
    return render(request, 'user_site/submissions.html')
