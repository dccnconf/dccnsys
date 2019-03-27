from django.shortcuts import render, redirect


def home(request):
    if not request.user.is_authenticated:
        return render(request, 'public_site/index.html')
    elif not request.user.has_finished_registration:
        return redirect('register')
    return redirect('submissions')
