from .base_settings import *
import dj_database_url
import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DATABASES = {'default': dj_database_url.config(conn_max_age=600)}

INTERNAL_IPS = ['127.0.0.1', 'localhost']
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = []
if os.environ.get('DOMAIN'):
    CSRF_TRUSTED_ORIGINS.append(f'https://{os.environ["DOMAIN"]}')

LOGGING = {}