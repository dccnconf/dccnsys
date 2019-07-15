"""
Django settings for wwwdccn project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from django.urls import reverse_lazy


def check_bool_env_var(name):
    return name in os.environ and os.environ[name] in {'y', 'yes', 'true', 'on'}


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REMOTE_DEPLOY = os.environ.get('DJANGO_REMOTE', False)

LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('home')
LOGOUT_REDIRECT_URL = reverse_lazy('home')

#####################################################
# Here we store current site domain and protocol:
SITE_PROTOCOL = os.environ.get('SITE_PROTOCOL', 'http')
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'localhost:8000')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
if REMOTE_DEPLOY:
    SECRET_KEY = os.environ['SECRET_KEY']
    ALLOWED_HOSTS = [os.environ['SITENAME']]
    DEBUG = False
    ADMINS = [(os.environ['ADMIN_NAME'], os.environ['ADMIN_EMAIL'])]
    USE_DEBUG_TOOLBAR = check_bool_env_var('USE_DEBUG_TOOLBAR')
else:
    # noinspection SpellCheckingInspection
    SECRET_KEY = '!unng-b4vbp6e=i^_gj!mrq56a88z4%6m2@_fhe8v!o*2k_%v*'
    ALLOWED_HOSTS = []
    DEBUG = True
    USE_DEBUG_TOOLBAR = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party applications:
    'bootstrap4',
    'anymail',
    'storages',
    'django_countries',
    'registration',

    # Application defined in this project:
    'users',
    'gears',
    'auth_app',
    'conferences',
    'submissions',
    'public_site',
    'user_site',
    'chair',
    'review',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wwwdccn.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'wwwdccn', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wwwdccn.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
if os.environ.get('DATABASE_PROVIDER', '') == 'postgresql':
    DB_NAME = os.environ['DB_NAME']
    DB_USERNAME = os.environ['DB_USERNAME']
    DB_PASSWORD = os.environ['DB_PASSWORD']
    DB_HOST = os.environ['DB_HOST']
    DB_PORT = os.environ.get('DB_PORT', '')

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': DB_NAME,
            'USER': DB_USERNAME,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        },
    }


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Define custom user model:
AUTH_USER_MODEL = 'users.User'


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
#################################################################
# Static files settings
#
# -- Environment variables:
# * STATIC_PROVIDER (opt.), 'selcdn' or 'local'
#
# If MEDIA_PROVIDER == 'selcdn', then we need the following variables:
# * SELCDN_HTTP_HOST - e.g. 239120.selcdn.ru (without https:// or slashes)
# * SELCDN_USERNAME
# * SELCDN_PASSWORD
# * SELCDN_STATIC_BIN (!! without slashes)
#################################################################
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

if os.environ.get('STATIC_PROVIDER', '') == 'selcdn':
    SELCDN_HTTP_HOST = os.environ['SELCDN_HTTP_HOST']
    SELCDN_USERNAME = os.environ['SELCDN_USERNAME']
    SELCDN_PASSWORD = os.environ['SELCDN_PASSWORD']
    SELCDN_STATIC_BIN = os.environ['SELCDN_STATIC_BIN']

    STATICFILES_STORAGE = 'wwwdccn.storages.StaticSFTPStorage'
    STATIC_URL = f'https://{SELCDN_HTTP_HOST}/{SELCDN_STATIC_BIN}/'
    STATIC_SFTP_STORAGE_ROOT = f'/{SELCDN_STATIC_BIN}/'
    STATIC_SFTP_STORAGE_HOST = 'ftp.selcdn.ru'
    STATIC_SFTP_STORAGE_PARAMS = {
        'username': SELCDN_USERNAME,
        'password': SELCDN_PASSWORD,
    }
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'static_dist')
    STATIC_URL = '/static/'


#################################################################
# Media settings
#
# -- Environment variables:
# * MEDIA_PROVIDER (opt.), 'selcdn' or 'local'
#
# If MEDIA_PROVIDER == 'selcdn', then we need the following variables:
# * SELCDN_HTTP_HOST - e.g. 239120.selcdn.ru (without https:// or slashes)
# * SELCDN_USERNAME
# * SELCDN_PASSWORD
# * SELCDN_MEDIA_PUBLIC_BIN (!! without slashes)
# * SELCDN_MEDIA_PRIVATE_BIN (!! without slashes)
#################################################################
if os.environ.get('MEDIA_PROVIDER', '') == 'selcdn':
    SELCDN_HTTP_HOST = os.environ['SELCDN_HTTP_HOST']
    SELCDN_USERNAME = os.environ['SELCDN_USERNAME']
    SELCDN_PASSWORD = os.environ['SELCDN_PASSWORD']
    SELCDN_MEDIA_PUBLIC_BIN = os.environ['SELCDN_MEDIA_PUBLIC_BIN']
    SELCDN_MEDIA_PRIVATE_BIN = os.environ['SELCDN_MEDIA_PRIVATE_BIN']

    USE_LOCAL_MEDIA = False
    MEDIA_URL = f'https://{SELCDN_HTTP_HOST}/'
    DEFAULT_FILE_STORAGE = 'storages.backends.sftpstorage.SFTPStorage'
    SFTP_STORAGE_HOST = 'ftp.selcdn.ru'
    SFTP_STORAGE_ROOT = '/'
    SFTP_STORAGE_PARAMS = {
        'username': SELCDN_USERNAME,
        'password': SELCDN_PASSWORD,
    }
    MEDIA_PUBLIC_ROOT = f'{SELCDN_MEDIA_PUBLIC_BIN}/'
    MEDIA_PRIVATE_ROOT = f'{SELCDN_MEDIA_PRIVATE_BIN}/'
else:
    USE_LOCAL_MEDIA = True
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    MEDIA_URL = '/media/'
    MEDIA_PUBLIC_ROOT = 'public/'
    MEDIA_PRIVATE_ROOT = 'private/'


#################################################################
# Email service settings
#
# -- Environment variables:
# * EMAIL_DOMAIN (opt.)
# * EMAIL_FROM (opt.), e.g. 'support@x.y.z'
# * EMAIL_PROVIDER (opt.), e.g. 'mailgun' or 'local'
# * EMAIL_FROM_SERVER (opt., if provider is mailgun)
# * MAILGUN_TOKEN
# * MAILGUN_API_URL (opt., by default - euro domain)
#################################################################
EMAIL_DOMAIN = os.environ.get('EMAIL_DOMAIN', 'mail.localhost')
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_FROM', f'support@{EMAIL_DOMAIN}')

if os.environ.get('EMAIL_PROVIDER', '') == 'mailgun':
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    SERVER_EMAIL = os.environ.get('SERVER_EMAIL_FROM', f'server@{EMAIL_DOMAIN}')

    ANYMAIL = {
        "MAILGUN_API_KEY": os.environ['MAILGUN_TOKEN'],
        "MAILGUN_SENDER_DOMAIN": EMAIL_DOMAIN,
        "MAILGUN_API_URL": os.environ.get(
            'MAILGUN_API_URL', "https://api.eu.mailgun.net/v3")
    }
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


BOOTSTRAP4 = {
    'required_css_class': 'required',
}


#######################
# NOCAPTCHA-RECAPTCHA
if REMOTE_DEPLOY:
    RECAPTCHA_SITE_KEY = os.environ['RECAPTCHA_SITE_KEY']
    RECAPTCHA_SECRET_KEY = os.environ['RECAPTCHA_SECRET_KEY']
else:
    RECAPTCHA_SITE_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
    RECAPTCHA_SECRET_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'


######################
# DEBUG TOOLBAR
if USE_DEBUG_TOOLBAR:
    # DEBUG = True
    INTERNAL_IPS = ['localhost', '127.0.0.1']
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]

    INSTALLED_APPS += [
        'debug_toolbar',
    ]

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }


    def show_toolbar(request):
        return True

    SHOW_TOOLBAR_CALLBACK = show_toolbar


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'wwwdccn.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}