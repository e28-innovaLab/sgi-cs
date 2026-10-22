"""Pruebas aisladas, sin necesitar un servidor PostgreSQL local."""

from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {**REST_FRAMEWORK, 'TEST_REQUEST_DEFAULT_FORMAT': 'json'}  # noqa: F405
