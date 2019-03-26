from django.shortcuts import render, redirect


def home(request):
    if not request.user.is_authenticated:
        return render(request, 'public_site/index.html')
    return redirect('user-details', pk=request.user.pk)
