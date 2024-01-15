import typing
from base64 import b64decode, b64encode
from urllib.parse import parse_qsl, urlencode

if typing.TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from fastapi import Request

from typing import TypeVar

from fastapi import HTTPException

from fango.schemas import Cursor, Page
from fango.utils import replace_proto, reverse_ordering

T = TypeVar("T")


class CursorPagination:
    """
    DRF like cursor pagination class.

    """

    def __init__(self, request: "Request", page_size: int, ordering: tuple[str, ...]) -> None:
        self.request = request
        self.page_size = page_size
        self.ordering = ordering
        self.cursor = self.decode_cursor()

    def get_page(self, queryset: "QuerySet") -> list["Model"]:
        if self.cursor.reverse:
            queryset = queryset.order_by(*reverse_ordering(self.ordering))
        else:
            queryset = queryset.order_by(*self.ordering)

        if self.cursor.position is not None:
            order = self.ordering[0]
            is_reversed = order.startswith("-")
            order_attr = order.lstrip("-")

            if self.cursor.reverse != is_reversed:
                kwargs = {order_attr + "__lt": self.cursor.position}
            else:
                kwargs = {order_attr + "__gt": self.cursor.position}

            queryset = queryset.filter(**kwargs)

        results = list(queryset[self.cursor.offset : self.cursor.offset + self.page_size + 1])  # noqa: E203
        self.page = list(results[: self.page_size])

        if len(results) > len(self.page):
            has_following_position = True
            following_position = self._get_position_from_instance(results[-1], self.ordering)
        else:
            has_following_position = False
            following_position = None

        if self.cursor.reverse:
            self.page = list(reversed(self.page))

            self.has_next = (self.cursor.position is not None) or (self.cursor.offset > 0)
            self.has_previous = has_following_position
            if self.has_next:
                self.next_position = self.cursor.position
            if self.has_previous:
                self.previous_position = following_position
        else:
            self.has_next = has_following_position
            self.has_previous = (self.cursor.position is not None) or (self.cursor.offset > 0)
            if self.has_next:
                self.next_position = following_position
            if self.has_previous:
                self.previous_position = self.cursor.position

        return self.page

    def get_next_link(self) -> str | None:
        if not self.has_next:
            return None

        if self.page and self.cursor and self.cursor.reverse and self.cursor.offset != 0:
            compare = self._get_position_from_instance(self.page[-1], self.ordering)
        else:
            compare = self.next_position

        offset, position = 0, None

        has_item_with_unique_position = False
        for item in reversed(self.page):
            position = self._get_position_from_instance(item, self.ordering)
            if position != compare:
                has_item_with_unique_position = True
                break

            compare = position
            offset += 1

        if self.page and not has_item_with_unique_position:
            if not self.has_previous:
                offset = self.page_size
                position = None
            elif self.cursor.reverse:
                offset = 0
                position = self.previous_position
            else:
                offset = self.cursor.offset + self.page_size
                position = self.previous_position

        if not self.page:
            position = self.next_position

        return self.encode_cursor(Cursor(offset=offset, reverse=False, position=position))

    def get_previous_link(self) -> str | None:
        if not self.has_previous:
            return None

        if self.page and self.cursor and not self.cursor.reverse and self.cursor.offset != 0:
            compare = self._get_position_from_instance(self.page[0], self.ordering)
        else:
            compare = self.previous_position

        offset, position = 0, None

        has_item_with_unique_position = False
        for item in self.page:
            position = self._get_position_from_instance(item, self.ordering)
            if position != compare:
                has_item_with_unique_position = True
                break

            compare = position
            offset += 1

        if self.page and not has_item_with_unique_position:
            if not self.has_next:
                offset = self.page_size

            elif self.cursor.reverse:
                offset = self.cursor.offset + self.page_size
                position = self.next_position
            else:
                offset = 0
                position = self.next_position

        if not self.page:
            position = self.previous_position

        return self.encode_cursor(Cursor(offset=offset, reverse=True, position=position))

    def decode_cursor(self) -> Cursor:
        try:
            encoded_cursor = self.request.query_params.get("cursor", "")
            tokens = dict(parse_qsl(b64decode(encoded_cursor.encode()).decode()))
            offset = int(tokens.get("o", 0))
            reverse = bool(int(tokens.get("r", 0)))
            position = tokens.get("p")
            return Cursor(offset=offset, reverse=reverse, position=position)
        except (TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Invalid cursor.")

    def encode_cursor(self, cursor: Cursor) -> str:
        tokens = {}
        if cursor.offset:
            tokens["o"] = cursor.offset
        if cursor.reverse:
            tokens["r"] = 1
        if cursor.position is not None:
            tokens["p"] = cursor.position

        querystring = urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode()).decode()
        return str(self.request.url.include_query_params(cursor=encoded))

    def _get_position_from_instance(self, instance: "dict | Model", ordering: tuple[str, ...]) -> str:
        field_name = ordering[0].lstrip("-")
        if isinstance(instance, dict):
            attr = instance[field_name]
        else:
            attr = getattr(instance, field_name)
        return str(attr)

    def get_page_response(self, data) -> Page:
        return Page(
            next=replace_proto(self.get_next_link()),
            previous=replace_proto(self.get_previous_link()),
            results=data,
        )
