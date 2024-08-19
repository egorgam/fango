import contextlib
from unittest import mock

import pytest
from django.db import connections


@pytest.fixture
def fix_asgiref_rollback():
    """
    Fixture for fix Rollback in Django ORM async context in asgi > 3.8.0

    """
    main_thread_local = connections._connections  # type: ignore
    for conn in connections.all():
        conn.inc_thread_sharing()

    main_thread_default_conn = main_thread_local._storage.default
    main_thread_storage = main_thread_local._lock_storage

    @contextlib.contextmanager
    def _lock_storage():
        yield mock.Mock(default=main_thread_default_conn)

    try:
        with mock.patch.object(main_thread_default_conn, "close"):
            object.__setattr__(main_thread_local, "_lock_storage", _lock_storage)
            yield
    finally:
        object.__setattr__(main_thread_local, "_lock_storage", main_thread_storage)
