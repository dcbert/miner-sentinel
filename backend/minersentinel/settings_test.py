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

# Simplify logging during tests
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