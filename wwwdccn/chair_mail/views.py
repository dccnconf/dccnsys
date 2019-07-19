from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET

from chair.utility import validate_chair_access
from conferences.models import Conference


@require_GET
def overview(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    template_html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" 
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <title>{{ subject }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>

<body style="margin: 0; padding: 0;">
<table align="center" border="0" cellpadding="0" cellspacing="0" max-width="600" 
       style="border-collapse: collapse;">
  <tr bgcolor="#fff" style="border-bottom: 1px solid #ddd;">
    <td align="center" bgcolor="#fff" style="padding: 2px 10px;">
      <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td>
            <img src="http://2019.dccn.ru/images/dccn-logo.png" alt="DCCN Logo" width="50" height="50" 
                 style="vertical-align: middle; margin-right: 10px;" />
          </td>
          <td>
            <p style="font-size: 1.2rem; font-weight: normal; font-family: Verdana, Geneva, sans-serif; color: #888;">
              International Conference on Distributed Computer and Communication Networks
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr bgcolor="#ffffff">
    <td bgcolor="#ffffff" style="padding: 10px 10px 30px 10px;">
      <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td>{{ body }}</td>
        </tr>
        <tr>
          <td>
            <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; margin: 10px 0 2px 0; padding-bottom: 0; color: #222;">
              Happy conferencing,
            </p>
            <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; margin: 0 0 2px 0; padding: 0; color: #222;">
              DCCN Organization Committee
            </p>
            <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; margin: 0; padding: 0; color: #222;">
              Contact us: <a href="mailto:org@dccn.ru">org@dccn.ru</a>
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <tr bgcolor="#fff" style="border-top: 1px solid #eee;">
    <td style="padding: 2px 10px 2px 10px; text-align: justify;">
      <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; color: #888;">
        This email was generated automatically due to actions performed at <a href="{{ site_url }}">{{ site_url }}</a>. 
        If you received this email unintentionally, please <a href="mailto:org@dccn.ru">contact us</a> and delete this email.
      </p>
    </td>
  </tr>
</table>
</body>

</html>"""
    template_plain = """
{{ body}}

Happy conferencing,
DCCN Organization Committee
Contact us: org@dccn.ru

----
This email was generated automatically due to actions performed at {{ site_url }}. 
If you received this email unintentionally, please contact us via org@dccn.ru and delete this email.
"""

    return render(request, 'chair_mail/overview.html', context={
        'conference': conference,
        'template_html': template_html,
        'template_plain': template_plain,
    })


def html_template(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)
    template_html = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" 
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
      <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
      <title>{{ subject }}</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    </head>

    <body style="margin: 0; padding: 0;">
    <table align="center" border="0" cellpadding="0" cellspacing="0" max-width="600" 
           style="border-collapse: collapse;">
      <tr bgcolor="#fff" style="border-bottom: 1px solid #ddd;">
        <td align="center" bgcolor="#fff" style="padding: 2px 10px;">
          <table border="0" cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td>
                <img src="http://2019.dccn.ru/images/dccn-logo.png" alt="DCCN Logo" width="50" height="50" 
                     style="vertical-align: middle; margin-right: 10px;" />
              </td>
              <td>
                <p style="font-size: 1.2rem; font-weight: normal; font-family: Verdana, Geneva, sans-serif; color: #888;">
                  International Conference on Distributed Computer and Communication Networks
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
      <tr bgcolor="#ffffff">
        <td bgcolor="#ffffff" style="padding: 10px 10px 30px 10px;">
          <table border="0" cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td>{{ body }}</td>
            </tr>
            <tr>
              <td>
                <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; margin: 10px 0 2px 0; padding-bottom: 0; color: #222;">
                  Happy conferencing,
                </p>
                <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; margin: 0 0 2px 0; padding: 0; color: #222;">
                  DCCN Organization Committee
                </p>
                <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; margin: 0; padding: 0; color: #222;">
                  Contact us: <a href="mailto:org@dccn.ru">org@dccn.ru</a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <tr bgcolor="#fff" style="border-top: 1px solid #eee;">
        <td style="padding: 2px 10px 2px 10px; text-align: justify;">
          <p style="font-size: 0.9rem; font-weight: lighter; font-family: sans-serif; color: #888;">
            This email was generated automatically due to actions performed at <a href="{{ site_url }}">{{ site_url }}</a>. 
            If you received this email unintentionally, please <a href="mailto:org@dccn.ru">contact us</a> and delete this email.
          </p>
        </td>
      </tr>
    </table>
    </body>

    </html>"""

    return render(request, 'chair_mail/template_html.html', context={
        'conference': conference,
        'template_html': template_html,
    })


def plain_template(request, conf_pk):
    conference = get_object_or_404(Conference, pk=conf_pk)
    validate_chair_access(request.user, conference)

    template_plain = """
{{ body}}

Happy conferencing,
DCCN Organization Committee
Contact us: org@dccn.ru

----
This email was generated automatically due to actions performed at {{ site_url }}. 
If you received this email unintentionally, please contact us via org@dccn.ru and delete this email.
"""

    return render(request, 'chair_mail/template_plain.html', context={
        'conference': conference,
        'template_plain': template_plain,
    })
