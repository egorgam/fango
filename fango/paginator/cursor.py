import typing

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet
    from fastapi import Request

from base64 import b64decode, b64encode
from typing import TypeVar

from fango.paginator.schemas import Page

T = TypeVar("T")


class CursorPagination:
    """
    DRF like cursor pagination class with sync and async support.

    """

    def __init__(self, request: "Request", page_size: int) -> None:
        self.request = request
        self.has_more_data = False
        self.page_size = page_size

    def _decode_cursor(self) -> int | None:
        if position := self.request.query_params.get("cursor"):
            return int(b64decode(position))

    def _encode_cursor(self, position: int) -> str | None:
        cursor = b64encode(str(position).encode("ascii")).decode("ascii")
        return str(self.request.url.include_query_params(cursor=cursor))

    def get_page_ids(self, queryset: "QuerySet") -> list:
        """
        This method can be used in complex algorithms with annotations or aggregations.
        You can create two-step pipeline with data enrichment.

        """
        page = self._order_and_paginate(queryset)
        return list(page.only("id").values_list("id", flat=True))

    def get_page(self, queryset: "QuerySet") -> Page:
        """
        This method is most priority to simple get paginated data.

        """
        page = self._order_and_paginate(queryset)
        return self.get_page_response([x for x in page])

    async def get_page_async(self, queryset: "QuerySet") -> Page:
        """
        This method is for using in async views. Unfortenatly Django not
        supports async filtering and slicing, and sync method is faster now.

        """
        page = self._order_and_paginate(queryset)
        return self.get_page_response([x async for x in page])

    def get_page_response(self, data: list) -> Page:
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

    def _order_and_paginate(self, queryset: "QuerySet") -> "QuerySet":
        """
        Base logic of cursor pagination.

        """
        ordering = queryset.model._meta.ordering
        self.reverse = "-" in ordering[0]
        self.ordering_field = ordering[0].lstrip("-")

        self.position = self._decode_cursor()

        queryset = queryset.order_by(*ordering)

        if self.position is not None:
            if self.reverse:
                lookup = {f"{self.ordering_field}__lt": self.position}
            else:
                lookup = {f"{self.ordering_field}__gt": self.position}

            queryset = queryset.filter(**lookup)

        return queryset[: self.page_size + 1]

    def get_next_link(self, data: list) -> str | None:
        if not self.has_more_data:
            return None

        return self._encode_cursor(getattr(data[-1], self.ordering_field, data[-1][self.ordering_field]))

    def get_previous_link(self, data: list) -> str | None:
        if self.position:
            if self.reverse:
                position = getattr(data[0], self.ordering_field, data[0][self.ordering_field]) + self.page_size + 1
            else:
                position = max(self.position - self.page_size, 0)

            return self._encode_cursor(position)
