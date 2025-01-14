from .base_settings import *

# Use a constant secret key for tests
SECRET_KEY = 'django-insecure-test-key-not-for-production'

# Use an in-memory SQLite database for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use local memory cache for tests (needed for ratelimit)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Make password hashing faster in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Turn off debug mode and security settings for tests
DEBUG = False
SECURE_SSL_REDIRECT = False

# Simplified logging for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

HUEY = {
    'huey_class': 'huey.SqliteHuey',  # Use SQLite instead of Redis
    'immediate': True,  # Execute tasks immediately instead of queueing
    'filename': ':memory:',  # Use in-memory database
}

# Disable migrations during tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Email settings for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
EMAIL_CONFIGURED = True

# Disable CSRF checks in tests
MIDDLEWARE = [m for m in MIDDLEWARE if 'csrf' not in m.lower()] 