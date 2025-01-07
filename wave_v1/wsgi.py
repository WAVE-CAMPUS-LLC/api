"""
WSGI config for wave_v1 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")

application = get_wsgi_application()

app = application

from django.core.management import execute_from_command_line
port = int(os.environ.get("PORT", 8000))
execute_from_command_line(["manage.py", "runserver", f"0.0.0.0:{port}"])