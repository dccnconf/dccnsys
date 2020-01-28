# DCCN'2019 Conference Management System

Conference management system for DCCN'2019 conference implemented using full-stack Django with a bit of jQuery and Bootstrap 4. 

## About

The source code is availble under MIT license.

### Features

- multiple submission types
- multiple proceedings types and volumes
- customizable file types collected for each proceedings type
- end of submission and review is soft, each submission may be administrated individually
- advanced admin console (custom, not Django admin site)
- messaging system for sending emails to multiple submissions or multiple users, supports template variables
- export users and submissions with customizable attributes

### Limitations

- only one track supported
- submission and proceedings fields are not customizable
- no users separation between conferences from the admin view

### 3-rd party integrations

Most integrations can be easily replaced, right now the system work with the following services.

- [MailGun](https://www.mailgun.com/) - transactional email provider
- [TravisCI](https://travis-ci.com/) - continuous delivery to staging and production sites
- [VScale.io](https://vscale.io/) - cloud servers the system runs on
- [Selectel](https://selectel.ru/) - cloud S3-compatible storage for files and backups

### List of 3-rd party software libraries

- [Django](https://www.djangoproject.com/) - full-stack Python web framework
- [django-anymail](https://github.com/anymail/django-anymail) - Django email backends
- [django-bootstrap4](https://pypi.org/project/django-bootstrap4/) - simple blend of Bootstrap 4 with Django
- [django-countries](https://github.com/SmileyChris/django-countries) - countries choices for Django
- [django-storages](https://django-storages.readthedocs.io/en/latest/) - storages backends for Django
- [Fabric2](https://pypi.org/project/fabric2/) - Python library for executing shell commands remotely
- [gunicorn](https://gunicorn.org/) - Python WSGI HTTP server
- [NGINX](https://www.nginx.com/) - web server
- [jQuery](https://jquery.com/) - popular JavaScript library for easy DOM manipulation
- [jQueryUI](https://jqueryui.com/) - user interface components
- [Bootstrap 4](https://getbootstrap.com/) - CSS framework
- [FontAwesome](https://fontawesome.com/) - a very large icons library
- [CodeMirror](https://codemirror.net/) - versatile code and Markdown editor in JS
- [PrismJS](https://prismjs.com/) - syntax highligter
- [Bootbox](http://bootboxjs.com/) - modals for Bootstrap
- [MathJS](https://mathjs.org/) - math library for JS
- [ChartJS](https://www.chartjs.org/) - drawing charts in JS
- [SweetAlert2](https://sweetalert2.github.io/) - yet another modals library
- [Gulp](https://gulpjs.com/) - build system used in frontend
