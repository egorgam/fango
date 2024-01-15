import typing

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

from typing import Generic, TypeVar

from fastapi import APIRouter
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
