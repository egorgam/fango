import os

from django.core.wsgi import get_wsgi_application
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.wsgi import WSGIMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django_application = get_wsgi_application()

from django.contrib.auth.models import User  # noqa

from api import users  # noqa

application = FastAPI()
application.include_router(users.router)

application.mount("/django/", WSGIMiddleware(django_application))
application.mount("/static/", StaticFiles(directory="staticfiles"), name="static")
