from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def user_details(request):
    return render(request, 'user_site/submissions.html')
