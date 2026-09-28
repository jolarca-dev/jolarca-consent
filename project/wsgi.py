"""WSGI config for jolarca-consent project.

Deployment servers (gunicorn, uwsgi) MUST set DJANGO_SETTINGS_MODULE explicitly.
There is no safe default: dev settings inject a publicly known throwaway secret
key, and base settings refuses to start without DJANGO_SECRET_KEY. Defaulting to
dev here would let production serve traffic with a known key — the exact attack
the fail-closed guard in base.py prevents.
"""

import os

from django.core.exceptions import ImproperlyConfigured
from django.core.wsgi import get_wsgi_application

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    raise ImproperlyConfigured(
        "DJANGO_SETTINGS_MODULE is not set. The WSGI entry point refuses to "
        "default to dev settings. Set DJANGO_SETTINGS_MODULE to the target "
        "environment's settings module before starting the server."
    )

application = get_wsgi_application()
