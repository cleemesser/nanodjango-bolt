"""Shared fixtures for nanodjango-bolt tests."""

import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings before any tests run."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="test-secret-key",
            ROOT_URLCONF="__main__",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
        )
        django.setup()
