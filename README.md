# <img src='https://github.com/egorgam/fango/assets/13712792/e541fff2-3833-4f30-ba9b-09ea5c375077' width='30'> Fango

Metaframework for web with combined FastAPI and Django.

Why?

Django has async orm, but DRF is not supports it. But there is a nice FastAPI framework without native Django ORM mode and admin panel. So...

Organize your app like a djangoproject, and use FastAPI over django orm with FANGO. You only need create main.py in djangoproject app.

Example:

```
import os

from django.core.wsgi import get_wsgi_application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.wsgi import WSGIMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")

django_application = get_wsgi_application()

from fango.auth.middlewares import BearerTokenAuthBackend  # noqa
from fango.routing import private, public  # noqa
from fango.auth.views import *  # noqa
from api.views import products, users  # noqa

app = FastAPI()
app.add_middleware(AuthenticationMiddleware, backend=BearerTokenAuthBackend())
app.include_router(private)
app.include_router(public)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/", WSGIMiddleware(django_application))
```

Some built in features of fango:

1. Async cypher JWT auth
2. DRF-like cursor paginaton
