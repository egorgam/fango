# <img src='https://github.com/egorgam/fango/assets/13712792/e541fff2-3833-4f30-ba9b-09ea5c375077' width='30'> FANGO

Metaframework for web with combined FastAPI and Django.

Why?

Django has async orm, but DRF is not supports it. But there is a nice FastAPI framework without native Django ORM mode and admin panel. So...

Organize your app like a djangoproject, and use FastAPI over django orm with FANGO.


Some built in features of FANGO:

1. Async cypher JWT auth
2. DRF-like cursor paginaton
3. DRF-lile GenericViewSet
4. Adapter for save pydantic model data with ORM
5. FastAPI TestClient for pytest-django tests
6. Django-filter support
