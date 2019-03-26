from django.shortcuts import render, get_object_or_404

from .models import User

# Create your views here.
def user_details(request, pk):
    user = get_object_or_404(User, pk=pk)
    user_fields = user._meta.get_fields()
    profile_fields = user.profile._meta.get_fields()
    data = {name.name: getattr(user, name.name) for name in user_fields}
    data.update({name.name: getattr(user.profile, name.name) for name in profile_fields})
    print(data)
    return render(request, 'users/user_details.html', {'data': data})
