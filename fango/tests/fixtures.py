import pytest


@pytest.fixture
def fix_asgiref_rollback():
    """
    Fixture for fix Rollback in Django ORM async context.

    Source: https://github.com/django/channels/issues/1091#issuecomment-701361358

    """
    from unittest import mock

    from django.db import connections

    local = connections._connections  # type: ignore
    ctx = local._get_context_id()
    for conn in connections.all():
        conn.inc_thread_sharing()
    conn = connections.all()[0]
    old = local._get_context_id
    try:
        with mock.patch.object(conn, "close"):
            object.__setattr__(local, "_get_context_id", lambda: ctx)
            yield
    finally:
        object.__setattr__(local, "_get_context_id", old)
