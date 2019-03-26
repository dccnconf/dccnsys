from django.shortcuts import render, get_object_or_404

from .models import User

# Create your views here.
def user_details(request, pk):
    user = get_object_or_404(User, pk=pk)
    return render(request, 'users/user_details.html', {'user': user})
