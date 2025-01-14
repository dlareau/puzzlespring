import os

os.environ["DATABASE_URL"] = 'sqlite:///mydatabase'
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ['ENFORCE_SSL'] = 'False'
os.environ['DJANGO_ENABLE_DEBUG'] = 'True'

from .base_settings import *

INSTALLED_APPS = ['daphne'] + INSTALLED_APPS

SECRET_KEY = 'development_secret_key'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

ASGI_APPLICATION = 'server.asgi.application'

STATICFILES_DIRS = ["custom/static",]
STATIC_ROOT = "static/"
MEDIA_ROOT = "media/"

TEMPLATES[0]['DIRS'] = ['custom/templates/',  'media/trusted/',]

HUEY = {
    'huey_class': 'huey.SqliteHuey',  # Use SQLite instead of Redis
    'immediate': True,  # Execute tasks immediately instead of queueing
    'filename': ':memory:',  # Use in-memory database
}

GRIP_URL = ''

DJANGO_ALLOW_ASYNC_UNSAFE = True