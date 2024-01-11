import asyncio
from typing import Callable

from django.core.exceptions import SynchronousOnlyOperation
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

from fango.auth.repositories import get_user, get_user_async


class async_cached_property:
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if instance not in self.cache:
            result = self.func(instance)
            if asyncio.iscoroutine(result):
                result = asyncio.ensure_future(result)
            self.cache[instance] = result

        return self.cache[instance]


class FangoRequest(Request):
    @async_cached_property
    def user(self):
        try:
            return get_user(self)
        except SynchronousOnlyOperation:
            return get_user_async(self)


class FangoRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = FangoRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler


class ExcludeUnsetAPIRouter(APIRouter):
    def get(self, *args, **kwargs) -> Callable:
        return super().get(*args, **kwargs, response_model_exclude_unset=True)
