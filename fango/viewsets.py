import typing

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

from typing import Generic, TypeVar

from fastapi import APIRouter, Request
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class FangoGenericViewSet(Generic[T]):
    """
    Generic ViewSet implementation.

    """

    pydantic_schema: "T"
    queryset: "QuerySet"
    internal: "APIRouter"

    def __init__(self, router: "APIRouter", basename: str) -> None:
        self.router = router
        self.basename = basename
        self.include_router()

    def include_router(self) -> None:
        """
        Method for merge viewset internal router with true API router.

        • Original "route.endpoint" with klass method is replaced by instance method

        """
        for route in self.internal.routes:
            route.endpoint = getattr(self, route.name)  # type: ignore

        self.router.include_router(self.internal, prefix="/" + self.basename, tags=[self.basename])

    def get_queryset(self) -> "QuerySet":
        """
        Method for get queryset defined in ViewSet.

        """
        return self.queryset


class AsyncReadOnlyViewSet(FangoGenericViewSet, Generic[T]):
    internal: "APIRouter" = APIRouter()

    @internal.api_route("/", methods=["GET"])
    async def list(self, request: "Request") -> list[T]:
        return [self.pydantic_schema.model_validate(x, context={"request": request}) async for x in self.get_queryset()]

    @internal.api_route("/{pk}/", methods=["GET"])
    async def retrieve(self, request: "Request", pk: int) -> "T":
        entry = await self.get_queryset().aget(pk=pk)
        return self.pydantic_schema.model_validate(entry, context={"request": request})
