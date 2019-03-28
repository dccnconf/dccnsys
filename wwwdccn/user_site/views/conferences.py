from django.shortcuts import render


def conferences_list(request):
    return render(request, 'user_site/conferences/conferences_list.html')
