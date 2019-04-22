import os
import time
import warnings

import fabric2 as fabric
import paramiko
import requests
import json

# Disable warnings coming from Paramiko package:
warnings.filterwarnings(action='ignore', module='.*paramiko.*')

DEFAULTS = {
    'VM_PLAN': 'small',
    'VM_LOCATION': 'msk0',
    'VM_IMAGE': 'ubuntu_18.04_64_001_master',
    'VM_USER_NAME': 'dccnadm',
    'STATIC_PROVIDER': 'selcdn',
    'MEDIA_PROVIDER': 'selcdn',
    'CDN_FTP_HOST': 'ftp.selcdn.ru',
    'REPO_URL': 'https://github.com/dccnconf/dccnsys.git',
    'DB_PROVIDER': 'postgresql',
    'DB_NAME': 'dccndb',
    'DB_USER': 'dccndbadm',
    'DB_HOST': 'localhost',
    'DB_PORT': '',
    'CERT_YEAR': '2019',
    'MAX_BODY_SIZE': '15M',
    'EMAIL_PROVIDER': 'mailgun',

    # Staging-specific deploy defaults:
    'STAGING_REPO_BRANCH': 'master',

    # Production-specific deploy defaults:
    'PRODUCTION_REPO_BRANCH': 'release',
}


class Environment:
    def __init__(self, prefix=''):
        self._prefix = prefix
        self.SITENAME = self.env('SITENAME')
        self.VSCALE_TOKEN = self.env('VSCALE_TOKEN')
        self.VM_PLAN = self.env('VM_PLAN')
        self.VM_LOCATION = self.env('VM_LOCATION')
        self.VM_IMAGE = self.env('VM_IMAGE')
        self.VM_ROOT_PASS = self.env('VM_ROOT_PASS')
        self.VM_USER_NAME = self.env('VM_USER_NAME')
        self.VM_USER_PASS = self.env('VM_USER_PASS')
        self.CDN_FTP_HOST = self.env('CDN_FTP_HOST')
        self.CDN_HTTP_HOST = self.env('CDN_HTTP_HOST')
        self.CDN_SYS_USER = self.env('CDN_SYS_USER')
        self.CDN_SYS_PASS = self.env('CDN_SYS_PASS')
        self.CDN_USER = self.env('CDN_USER')
        self.CDN_PASS = self.env('CDN_PASS')
        self.CDN_CERT_PATH = self.env('CDN_CERT_PATH')
        self.CDN_STATIC_BIN = self.env('CDN_STATIC_BIN')
        self.CDN_MEDIA_PUBLIC_BIN = self.env('CDN_MEDIA_PUBLIC_BIN')
        self.CDN_MEDIA_PRIVATE_BIN = self.env('CDN_MEDIA_PRIVATE_BIN')
        self.STATIC_PROVIDER = self.env('STATIC_PROVIDER')
        self.MEDIA_PROVIDER = self.env('MEDIA_PROVIDER')
        self.REPO_URL = self.env('REPO_URL')
        self.BRANCH = self.env('REPO_BRANCH')
        self.DB_PROVIDER = self.env('DB_PROVIDER')
        self.DB_NAME = self.env('DB_NAME')
        self.DB_USER = self.env('DB_USER')
        self.DB_PASS = self.env('DB_PASS')
        self.DB_HOST = self.env('DB_HOST')
        self.DB_PORT = self.env('DB_PORT')
        self.CERT_YEAR = self.env('CERT_YEAR')
        self.MAX_BODY_SIZE = self.env('MAX_BODY_SIZE')
        self.EMAIL_PROVIDER = self.env('EMAIL_PROVIDER')
        self.EMAIL_DOMAIN = self.env('EMAIL_DOMAIN')
        self.EMAIL_FROM = self.env('EMAIL_FROM')
        self.SERVER_EMAIL_FROM = self.env('SERVER_EMAIL_FROM')
        self.MAILGUN_TOKEN = self.env('MAILGUN_TOKEN')
        self.MAILGUN_API_URL = self.env('MAILGUN_API_URL')
        self.SECRET_KEY = self.env('SECRET_KEY')
        self.RECAPTCHA_SITE_KEY = self.env('RECAPTCHA_SITE_KEY')
        self.RECAPTCHA_SECRET_KEY = self.env('RECAPTCHA_SECRET_KEY')

        # Derivatives and constants:
        self.DOMAIN = '.'.join(self.SITENAME.split('.')[-2:])
        self.UBUNTU_PACKAGES = (
            'python3.6', 'nginx', 'postgresql', 'sshpass', 'git', 'vim',
            'python3-venv',
        )
        self.DJANGO_PROJECT_NAME = 'wwwdccn'

    def env(self, name):
        full_name = f'{self._prefix}_{name}' if self._prefix else name
        if full_name in os.environ:
            return os.environ[full_name]
        elif name in os.environ:
            return os.environ[name]
        elif full_name in DEFAULTS:
            return DEFAULTS[full_name]
        return DEFAULTS[name]


ENVIRONMENT_PREFIXES = {
    'staging': 'STAGING',
    'production': 'PRODUCTION',
}


def environment(env_type='staging'):
    return Environment(ENVIRONMENT_PREFIXES[env_type])


@fabric.task
def create_server(ctx, name, envtype):
    assert not isinstance(ctx, fabric.Connection)  # no support fo --host arg

    env = environment(envtype)

    # 1) Create new scalet, bind DNS to it and add address to known_hosts:
    address = create_scalet(name, env=env)
    update_dns(address, env=env)

    # 2) Establish a connection with root access rights to install software,
    # create admin user and copy certificates:
    root = fabric.Connection(address, user='root', connect_kwargs={
        'password': env.VM_ROOT_PASS
    })
    root.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    install_system_packages(root, env=env)
    copy_certificates(root, env=env)
    create_user(root, env=env)

    # 3) Establish a connection on part of the non-root user (site admin),
    # prepare home folder, clone the repository and setup the database:
    user = fabric.Connection(address, user=env.VM_USER_NAME, connect_kwargs={
        'password': env.VM_USER_PASS
    })
    user.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    clone_repo(user, env=env)
    write_env(user, env=env)
    create_database(user, env=env)

    # 4) On part of root, create configuration files and services:
    create_gunicorn_service(root, env=env)
    create_nginx_config(root, env=env)

    # 5) Update the repository, make migrations, install python packages.
    # Then tart services (on part of root).
    update_repo(user, env=env)
    gunicorn_service(root, 'start', env=env)
    nginx_service(root, 'restart')


# noinspection PyUnusedLocal
@fabric.task
def update(ctx, envtype):
    assert not isinstance(ctx, fabric.Connection)  # no support fo --host arg
    env = environment(envtype)

    root = fabric.Connection(
        env.SITENAME, user='root', connect_kwargs={
            'password': env.VM_ROOT_PASS
        }
    )
    user = fabric.Connection(
        env.SITENAME, user=env.VM_USER_NAME, connect_kwargs={
            'password': env.VM_USER_PASS
        }
    )
    for conn in (root, user):
        conn.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Load changes, write .env:
    write_env(user, env)
    update_repo(user, env)

    # Update services configurations and restart them:
    gunicorn_service(root, 'stop', env)
    nginx_service(root, 'stop')
    create_gunicorn_service(root, env)
    create_nginx_config(root, env)
    gunicorn_service(root, 'start', env)
    nginx_service(root, 'start')


def vscale(url, method='get', data=None, token=''):
    fn = getattr(requests, method)
    headers = {'X-Token': token}
    if data:
        headers['Content-Type'] = 'application/json;charset=UTF-8'
        response = fn(url, headers=headers, data=json.dumps(data))
    else:
        response = fn(url, headers=headers)
    if 200 <= response.status_code <= 299:
        return response.json()
    raise RuntimeError(response)


def create_scalet(name, env):
    print('[FAB] * create_scalet()')
    response = vscale('https://api.vscale.io/v1/scalets', method='post', data={
        'make_from': env.VM_IMAGE,
        'name': name,
        'rplan': env.VM_PLAN,
        'do_start': True,
        'password': env.VM_ROOT_PASS,
        'location': env.VM_LOCATION,
    }, token=env.VSCALE_TOKEN)
    ctid = response['ctid']
    while response['status'] != 'started':
        time.sleep(1)
        response = vscale(
            f'https://api.vscale.io/v1/scalets/{ctid}',
            token=env.VSCALE_TOKEN
        )
    return response['public_address']['address']


def update_dns(address, env, ttl=300):
    print('[FAB] * update_dns()')
    # 1) First we find the domain ID:
    response = vscale(
        'https://api.vscale.io/v1/domains',
        token=env.VSCALE_TOKEN
    )
    dom_id = [rec['id'] for rec in response if rec['name'] == env.DOMAIN][0]

    # 2) Then we list all domain records related to this domain and try to find
    # the record related to our site:
    all_sites = vscale(
        f'https://api.vscale.io/v1/domains/{dom_id}/records',
        token=env.VSCALE_TOKEN
    )

    # 3) Since we need both sitename (e.g. example.com) and www.sitename,
    # we iterate through these names in cycle:
    for name in (env.SITENAME, f'www.{env.SITENAME}'):
        records = [rec for rec in all_sites
                   if rec['name'] == name and rec['type'] in {'A', 'CNAME'}]
        assert 0 <= len(records) <= 1

        data = {
            'content': address,
            'ttl': ttl,
            'type': 'A',
            'name': name
        }

        # 4) If there is no site records, we create one:
        if not records:
            vscale(f'https://api.vscale.io/v1/domains/{dom_id}/records/',
                   method='post', data=data, token=env.VSCALE_TOKEN)
            continue

        # 5) If name was already registered, we need to find this record and
        # make sure that its type is 'A'. If its type is 'CNAME', we need to
        # first delete that record (otherwise, Vscale API will return 400).
        # Otherwise, we issue PUT request to update the record.
        rid = records[0]['id']
        if records[0]['type'] != data['type']:
            vscale(f'https://api.vscale.io/v1/domains/{dom_id}/records/{rid}',
                   method='delete', token=env.VSCALE_TOKEN)
            vscale(f'https://api.vscale.io/v1/domains/{dom_id}/records/',
                   method='post', data=data, token=env.VSCALE_TOKEN)
        else:
            vscale(f'https://api.vscale.io/v1/domains/{dom_id}/records/{rid}',
                   method='put', data=data, token=env.VSCALE_TOKEN)


def copy_certificates(c, env):
    local_path = f'/etc/ssl/'
    remote_path = f'{env.CDN_SYS_USER}@{env.CDN_FTP_HOST}:/{env.CDN_CERT_PATH}'
    ftp = f'SSHPASS={env.CDN_SYS_PASS} sshpass -e sftp {remote_path}'

    c.run('mkdir -p ~/.ssh', echo=True)
    c.run(f'ssh-keyscan -H {env.CDN_FTP_HOST} >> ~/.ssh/known_hosts', echo=True)
    c.run(f'mkdir -p {local_path}', echo=True)
    c.run(f'{ftp}/{env.SITENAME}*.crt /etc/ssl/certs/', echo=True)
    c.run(f'{ftp}/{env.SITENAME}*.key /etc/ssl/private/', echo=True)


def create_user(c, env):
    adduser = c.run(
        f'adduser --quiet --disabled-password --gecos "" {env.VM_USER_NAME}',
        warn=True, echo=True
    )
    if adduser.exited == 0:
        c.run(f'echo "{env.VM_USER_NAME}:{env.VM_USER_PASS}" | chpasswd')
        c.run(f'echo "{env.VM_USER_NAME} ALL=(postgres) NOPASSWD: ALL" >> '
              f'/etc/sudoers')


def install_system_packages(c, env):
    packages_string = ' '.join(env.UBUNTU_PACKAGES)
    c.run(f'apt update; apt-get -y install {packages_string}', echo=True)


def clone_repo(c, env):
    c.run(f'mkdir -p /home/{env.VM_USER_NAME}/sites', echo=True)
    with c.cd(f'/home/{env.VM_USER_NAME}/sites'):
        c.run(f'rm -rf {env.SITENAME}', echo=True)
        c.run(f'git clone {env.REPO_URL} {env.SITENAME}', echo=True)
        with c.cd(env.SITENAME):
            c.run(f'python3 -m venv --prompt {env.SITENAME} .venv', echo=True)


def update_repo(c, env):
    print('>>>>>> branch: ', env.BRANCH)
    with c.cd(f'/home/{env.VM_USER_NAME}/sites/{env.SITENAME}'):
        c.run(f'git branch --set-upstream-to origin/{env.BRANCH}', echo=True)
        c.run(f'git fetch', echo=True)
        c.run(f'git checkout --force {env.BRANCH}', echo=True)
        c.run(f'git reset --hard `git log --all -n 1 --format=%H {env.BRANCH}`',
              echo=True)
        c.run(f'.venv/bin/pip install --upgrade pip', echo=True)
        c.run(f'.venv/bin/pip install -r requirements.txt', echo=True)
        with c.cd(env.DJANGO_PROJECT_NAME):
            manage = '../.venv/bin/python manage.py'
            env_cmd = f'export $(cat ../.env | xargs)'
            c.run(f'{env_cmd}; {manage} collectstatic --noinput')
            c.run(f'{env_cmd}; {manage} migrate --noinput', echo=True)


def create_database(c, env):
    def psql(cmd):
        return f'sudo -u postgres psql -qc "{cmd};"'

    db = env.DB_NAME
    user = env.DB_USER
    password = env.DB_PASS

    # noinspection SqlNoDataSourceInspection,SqlDialectInspection
    c.run(psql(f"CREATE DATABASE {db}"), warn=True, echo=True)
    c.run(psql(f"CREATE USER {user} WITH PASSWORD '{password}'"), warn=True,
          echo=True)
    c.run(psql(f"ALTER ROLE {user} SET client_encoding TO 'utf-8'"), echo=True)
    c.run(psql(f"ALTER ROLE {user} SET default_transaction_isolation TO "
               "'read committed'"), echo=True)
    c.run(psql(f"ALTER ROLE {user} SET timezone TO 'Europe/Moscow'"), echo=True)
    c.run(psql(f"GRANT ALL PRIVILEGES ON DATABASE {db} TO {user}"), echo=True)


def create_gunicorn_service(c, env):
    assignments = {
        'SITENAME': env.SITENAME,
        'USERNAME': env.VM_USER_NAME,
        'PROJNAME': env.DJANGO_PROJECT_NAME,
    }
    pattern = ";".join([f's/{k}/{v}/g' for k, v in assignments.items()])
    deploy_path = f'/home/{env.VM_USER_NAME}/sites/{env.SITENAME}/deploy/'
    service_name = f'gunicorn-{env.SITENAME}'
    c.run(f'cat {deploy_path}/gunicorn.service | '
          f'sed "{pattern}" > /etc/systemd/system/{service_name}.service',
          echo=True)
    c.run(f'systemctl daemon-reload; systemctl enable {service_name}',
          echo=True)


def create_nginx_config(c, env):
    assignments = {
        'SITENAME': env.SITENAME,
        'MAX_BODY_SIZE': env.MAX_BODY_SIZE,
        'YEAR': env.CERT_YEAR,
    }

    user = env.VM_USER_NAME
    site = env.SITENAME
    pattern = ";".join([f's/{k}/{v}/g' for k, v in assignments.items()])

    c.run(f'cat /home/{user}/sites/{site}/deploy/sitename.nginx |'
          f'sed "{pattern}" > /etc/nginx/sites-available/{site}',
          echo=True)
    c.run(f'cat /home/{user}/sites/{site}/deploy/www.sitename.nginx |'
          f'sed "{pattern}" > /etc/nginx/sites-available/www.{site}',
          echo=True)
    with c.cd('/etc/nginx/sites-available'):
        c.run(f'ln -frs {site} ../sites-enabled/{site}', echo=True)
        c.run(f'ln -frs www.{site} ../sites-enabled/www.{site}',
              echo=True)
        c.run(f'rm -f ../sites-enabled/default', echo=True)


def gunicorn_service(c, cmd, env):
    c.run(f'systemctl {cmd} gunicorn-{env.SITENAME}', echo=True)


def nginx_service(c, cmd):
    c.run(f'systemctl {cmd} nginx', echo=True)


def write_env(c, env):
    assignments = {
        'DJANGO_REMOTE': 1,
        'SITENAME': env.SITENAME,
        'SECRET_KEY': env.SECRET_KEY,
        'STATIC_PROVIDER': env.STATIC_PROVIDER,
        'MEDIA_PROVIDER': env.MEDIA_PROVIDER,
        'SELCDN_HTTP_HOST': env.CDN_HTTP_HOST,
        'SELCDN_USERNAME': env.CDN_USER,
        'SELCDN_PASSWORD': env.CDN_PASS,
        'SELCDN_STATIC_BIN': env.CDN_STATIC_BIN,
        'SELCDN_MEDIA_PRIVATE_BIN': env.CDN_MEDIA_PRIVATE_BIN,
        'SELCDN_MEDIA_PUBLIC_BIN': env.CDN_MEDIA_PUBLIC_BIN,
        'EMAIL_PROVIDER': env.EMAIL_PROVIDER,
        'EMAIL_DOMAIN': env.EMAIL_DOMAIN,
        'EMAIL_FROM': env.EMAIL_FROM,
        'SERVER_EMAIL_FROM': env.SERVER_EMAIL_FROM,
        'MAILGUN_TOKEN': env.MAILGUN_TOKEN,
        'MAILGUN_API_URL': env.MAILGUN_API_URL,
        'DATABASE_PROVIDER': env.DB_PROVIDER,
        'DB_NAME': env.DB_NAME,
        'DB_USERNAME': env.DB_USER,
        'DB_PASSWORD': env.DB_PASS,
        'DB_HOST': env.DB_HOST,
        'DB_PORT': env.DB_PORT,
        'RECAPTCHA_SITE_KEY': env.RECAPTCHA_SITE_KEY,
        'RECAPTCHA_SECRET_KEY': env.RECAPTCHA_SECRET_KEY,
    }

    with c.cd(f'/home/{env.VM_USER_NAME}/sites/{env.SITENAME}'):
        c.run('rm -f .env && touch .env', echo=True)
        for var, value in assignments.items():
            if var == 'SECRET_KEY':
                value = f"'{value}'"  # need to enclose in quotes this
            c.run(f'echo {var}={value} >> .env')
