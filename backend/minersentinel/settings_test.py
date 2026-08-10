"""
Test settings for Django backend test suite.
Uses SQLite in-memory for fast, isolated tests. No external services required.
"""
from .settings import *  # noqa: F401,F403


class _DisableMigrations:
    """Skip migrations in tests; Django uses syncdb from models directly.
    Necessary because several migrations contain Postgres-only RunSQL statements
    (ALTER TABLE ... SET DEFAULT) that fail on SQLite.
    """
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()

# Override database to SQLite for tests (fast, no postgres needed)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable debug for realistic test env
DEBUG = False

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Simplify logging during tests.
# disable_existing_loggers=True is required so Django's default AdminEmailHandler
# is not left attached to the django logger. On Python 3.14, that handler's
# ExceptionReporter path hits a BaseContext.__copy__ crash when the test client
# captures rendered templates for 500 responses (even with empty ADMINS).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['null'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# REST framework test friendly (keep session auth)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # type: ignore
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# Disable CSRF for API tests where needed
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Make tests deterministic
USE_TZ = True
TIME_ZONE = 'UTC'