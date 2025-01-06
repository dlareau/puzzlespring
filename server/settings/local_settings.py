from .base_settings import *
import ipaddress

DEBUG = True
SECRET_KEY = 'this is not the secret key, use your own'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase',
    }
}

docker_range = [str(ip) for ip in ipaddress.IPv4Network('172.17.0.0/24')]
INTERNAL_IPS = ['127.0.0.1', 'localhost'] + docker_range

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

MEDIA_ROOT = "media/"

# Sendfile settings
SENDFILE_BACKEND = "django_sendfile.backends.development"
SENDFILE_ROOT = MEDIA_ROOT

TEMPLATES[0]['DIRS'] = ['media/hunt', 'media/puzzle']

ALLOWED_HOSTS = ['*']
LOGGING = {

}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

CRISPY_FAIL_SILENTLY = not DEBUG
