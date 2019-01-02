"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

if os.environ.get('ENVIRONMENT') == 'DEVELOPMENT':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_dev")
if os.environ.get('ENVIRONMENT') == 'TESTING':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_dev")
if os.environ.get('ENVIRONMENT') == 'PRODUCTION':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_prod")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_dev")

application = get_wsgi_application()
