import csv
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from chair.forms import ExportSubmissionsForm, ExportUsersForm
from chair.utility import validate_chair_access
from conferences.models import Conference


def create_export_view(form_class, file_name_prefix, title):

    def view(request, conf_pk):
        conference = get_object_or_404(Conference, pk=conf_pk)
        validate_chair_access(request.user, conference)

        default_next = reverse('chair:home', kwargs={'conf_pk': conf_pk})
        next_url = request.GET.get('next', default_next)

        if request.method == 'POST':
            form = form_class(request.POST, conference=conference)
            if form.is_valid():
                data = form.apply(request)

                # Create the HttpResponse object with the appropriate header.
                response = HttpResponse(content_type='text/csv')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                response['Content-Disposition'] = \
                    f'attachment; filename="{file_name_prefix}-{timestamp}.csv"'
                writer = csv.writer(response)

                # import sys
                # writer = csv.writer(sys.stdout)
                writer.writerow(form.cleaned_data['columns'])
                for item in data:
                    row = []
                    for col in form.cleaned_data['columns']:
                        row.append(item[col])
                    writer.writerow(row)
                return response
        else:  # request was GET:
            form = form_class(conference=conference)

        return render(request, 'chair/export/export_dialog.html', context={
            'conference': conference,
            'next': next_url,
            'form': form,
            'panel_title': title,
        })

    return view


export_submissions = create_export_view(
    ExportSubmissionsForm, 'papers', 'Export submissions')

export_users = create_export_view(ExportUsersForm, 'users', 'Export users')
