from django.shortcuts import render


def render_conference_form(request, conference, form, subtitle):
    return render(request, 'user_site/conferences/conference_form.html', {
        'conference': conference,
        'form': form,
        'subtitle': subtitle,
    })
