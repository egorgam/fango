from django.core.exceptions import SynchronousOnlyOperation
from fastapi import Request

from fango.auth import get_user, get_user_async
from fango.utils import async_cached_property


class FangoRequest(Request):
    @async_cached_property
    def user(self):
        try:
            return get_user(self)
        except SynchronousOnlyOperation:
            return get_user_async(self)
