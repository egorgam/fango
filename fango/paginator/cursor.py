import re
import typing

if typing.TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from fastapi import Request

from base64 import b64decode, b64encode
from typing import TypeVar

from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
from django.db.models import Case, F
from fastapi import HTTPException

from fango.paginator.schemas import Page

T = TypeVar("T")


class CursorPagination:
    """
    DRF like cursor pagination class with sync and async support.

    """

    def __init__(self, request: "Request", page_size: int, ordering: tuple) -> None:
        self.request = request
        self.has_more_data = False
        self.page_size = page_size
        self.ordering = ordering

    def _decode_cursor(self) -> int | None:
        if position := self.request.query_params.get("cursor"):
            return int(b64decode(position))

    def _encode_cursor(self, position: int) -> str | None:
        cursor = b64encode(str(position).encode()).decode()
        return str(self.request.url.include_query_params(cursor=cursor))

    def get_page(self, queryset: "QuerySet") -> "QuerySet":
        """
        This method is most priority to simple get paginated data.

        """
        return self._order_and_paginate(queryset)

    async def get_page_async(self, queryset: "QuerySet") -> "QuerySet":
        """
        This method is for using in async views. Unfortenatly Django not
        supports async filtering and slicing, and sync method is faster now.

        """
        return self._order_and_paginate(queryset)

    def _order_and_paginate(self, queryset: "QuerySet") -> "QuerySet":
        """
        Base logic of cursor pagination.

        """
        self.reverse, self.ordering_field = re.match(r"(-?)(.*)", self.ordering[0]).groups()

        for field, annotation in queryset.query.annotations.items():
            if field == self.ordering_field:
                if type(annotation) in (StringAgg, ArrayAgg):
                    self.ordering_field = annotation._constructor_args[0][0]

                elif type(annotation) is Case:
                    self.ordering_field = annotation._constructor_args[0][0].result.name

                elif type(annotation) is F:
                    self.ordering_field = annotation._constructor_args[0].result.name

                else:
                    raise HTTPException(status_code=501, detail="Can't order by annotated field '%s'" % field)

        queryset = queryset.order_by(self.reverse + self.ordering_field)

        self.position = self._decode_cursor()

        if self.position is not None:
            if self.reverse:
                lookup = {f"{self.ordering_field}__lt": self.position}
            else:
                lookup = {f"{self.ordering_field}__gt": self.position}

            queryset = queryset.filter(**lookup)

        return queryset[: self.page_size + 1]

    def get_page_response(self, data: list["Model"]) -> Page:
        if len(data) > self.page_size:
            self.has_more_data = True
            data = data[:-1]
        else:
            self.has_more_data = False

        return Page(
            next=self.get_next_link(data),
            previous=self.get_previous_link(data),
            results=data,
        )

    def get_next_link(self, data: list["Model"]) -> str | None:
        if self.has_more_data:
            return self._encode_cursor(data[-1].pk)

    def get_previous_link(self, data: list["Model"]) -> str | None:
        if self.position:
            if self.reverse:
                position = data[0].pk + self.page_size + 1
            else:
                position = max(self.position - self.page_size, 0)

            return self._encode_cursor(position)
