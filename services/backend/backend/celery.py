from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

if os.environ.get('ENVIRONMENT') == 'DEVELOPMENT':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_dev")
if os.environ.get('ENVIRONMENT') == 'TESTING':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_dev")
if os.environ.get('ENVIRONMENT') == 'PRODUCTION':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_prod")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings_dev")

app = Celery('backend')
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()
