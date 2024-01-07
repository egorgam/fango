from base64 import b64decode, b64encode
from collections import namedtuple
from typing import TypeVar
from urllib import parse

from asgiref.sync import sync_to_async
from django.db.models import QuerySet
from django.utils.encoding import force_str
from paginator.schemas import Page

T = TypeVar("T")

Cursor = namedtuple("Cursor", ["offset", "reverse", "position"])


def replace_query_param(url, key, val):
    """
    Given a URL and a key/val pair, set or replace an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(force_str(url))
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[force_str(key)] = [force_str(val)]
    query = parse.urlencode(sorted(query_dict.items()), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


class CursorPagination:
    page_size = 15
    ordering = ("id",)

    def __init__(self, request) -> None:
        self.request = request
        self.cursor = self.decode_cursor()
        self.has_more_data = False

    def _positive_int(self, integer_string: str, strict: bool = False, cutoff: int | None = None) -> int:
        ret = int(integer_string)
        if ret < 0 or (ret == 0 and strict):
            raise ValueError()
        if cutoff:
            return min(ret, cutoff)
        return ret

    def decode_cursor(self) -> Cursor | None:
        offset_cutoff = 1000
        invalid_cursor_message = "Invalid cursor"
        cursor_query_param = "cursor"

        encoded = self.request.query_params.get(cursor_query_param)
        if encoded is None:
            return None

        try:
            querystring = b64decode(encoded.encode("ascii")).decode("ascii")
            tokens = parse.parse_qs(querystring, keep_blank_values=True)

            offset = tokens.get("o", ["0"])[0]
            offset = self._positive_int(offset, cutoff=offset_cutoff)

            reverse = tokens.get("r", ["0"])[0]
            reverse = bool(int(reverse))

            position = tokens.get("p", [None])[0]
        except (TypeError, ValueError):
            raise Exception(invalid_cursor_message)

        return Cursor(offset=offset, reverse=reverse, position=position)

    async def encode_cursor(self, cursor: Cursor) -> str:
        cursor_query_param = "cursor"

        tokens = {}
        if cursor.offset != 0:
            tokens["o"] = str(cursor.offset)
        if cursor.reverse:
            tokens["r"] = "1"
        if cursor.position is not None:
            tokens["p"] = cursor.position

        querystring = parse.urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode("ascii")).decode("ascii")
        return replace_query_param(self.request.url, cursor_query_param, encoded)

    async def paginate_queryset(self, queryset: QuerySet) -> Page:
        if self.cursor:
            offset = self.cursor.offset
            limit = offset + self.page_size + 1
        else:
            offset = 0
            limit = self.page_size + 1

        page_queryset = queryset[offset:limit]
        page_data = await sync_to_async(list)(page_queryset)

        if len(page_data) > self.page_size:
            self.has_more_data = True
            page_data = page_data[:-1]
        else:
            self.has_more_data = False

        return await self.get_paginated_response(page_data)

    async def get_paginated_response(self, data: list[QuerySet]) -> Page:
        return Page(
            previous=await self.get_previous_link(),
            next=await self.get_next_link(),
            results=data,
        )

    async def get_previous_link(self) -> str | None:
        if self.cursor:
            if self.cursor.offset < 2 * self.page_size:
                return await self.encode_cursor(Cursor(offset=0, reverse=False, position=self.page_size))

            position = self.cursor.offset - self.page_size
            return await self.encode_cursor(Cursor(offset=position, reverse=False, position=self.page_size))

    async def get_next_link(self) -> str | None:
        if self.cursor:
            new_offset = self.cursor.offset
        else:
            new_offset = 0

        if self.has_more_data:
            return await self.encode_cursor(
                Cursor(offset=new_offset + self.page_size, reverse=False, position=new_offset + self.page_size)
            )
