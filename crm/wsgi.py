import os

from django.core.wsgi import get_wsgi_application

os.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")

application = get_wsgi_application()
