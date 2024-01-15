from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

from fango.request import FangoRequest


class FangoRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = FangoRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler


class FangoRouter(APIRouter):
    def get(self, *args, **kwargs) -> Callable:
        return super().get(*args, **kwargs, response_model_exclude_unset=True)

    def register(self, basename: str, klass: type) -> None:
        klass(self, basename)
