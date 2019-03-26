from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404

User = get_user_model()

# Create your views here.
def user_details(request):
    user = request.user
    user_fields = user._meta.get_fields()
    profile_fields = user.profile._meta.get_fields()
    data = {name.name: getattr(user, name.name) for name in user_fields}
    data.update({name.name: getattr(user.profile, name.name) for name in profile_fields})
    return render(request, 'users/user_details.html', {'data': data})
