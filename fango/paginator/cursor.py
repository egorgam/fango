import typing

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet
    from fastapi import Request

from base64 import b64decode, b64encode
from collections import namedtuple
from typing import TypeVar
from urllib import parse

from django.utils.encoding import force_str

from fango.paginator.schemas import Page

T = TypeVar("T")

Cursor = namedtuple("Cursor", ["offset", "reverse", "position"])


class CursorPagination:
    """
    DRF like cursor pagination class with sync and async support.

    """

    def __init__(self, request: "Request", page_size: int) -> None:
        self.request = request
        self.cursor = self._decode_cursor()
        self.has_more_data = False
        self.page_size = page_size

    def _positive_int(self, integer_string: str, strict: bool = False, cutoff: int | None = None) -> int:
        ret = int(integer_string)
        if ret < 0 or (ret == 0 and strict):
            raise ValueError()
        if cutoff:
            return min(ret, cutoff)
        return ret

    def _decode_cursor(self) -> Cursor | None:
        encoded = self.request.query_params.get("cursor")
        if encoded is None:
            return None

        try:
            querystring = b64decode(encoded.encode("ascii")).decode("ascii")
            tokens = parse.parse_qs(querystring, keep_blank_values=True)

            offset = tokens.get("o", ["0"])[0]
            offset = self._positive_int(offset, cutoff=1000)

            reverse = tokens.get("r", ["0"])[0]
            reverse = bool(int(reverse))

            position = tokens.get("p", [None])[0]
        except (TypeError, ValueError):
            raise Exception("Invalid cursor")

        return Cursor(offset=offset, reverse=reverse, position=position)

    def _encode_cursor(self, cursor: Cursor) -> str:
        tokens = {}

        if cursor.offset != 0:
            tokens["o"] = str(cursor.offset)
        if cursor.reverse:
            tokens["r"] = "1"
        if cursor.position is not None:
            tokens["p"] = cursor.position

        querystring = parse.urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode("ascii")).decode("ascii")

        (scheme, netloc, path, query, fragment) = parse.urlsplit(force_str(self.request.url))
        query_dict = parse.parse_qs(query, keep_blank_values=True)
        query_dict[force_str("cursor")] = [force_str(encoded)]
        query = parse.urlencode(sorted(query_dict.items()), doseq=True)
        return parse.urlunsplit((scheme, netloc, path, query, fragment))

    def _paginate(self, queryset: "QuerySet") -> "QuerySet":
        """
        Base logic of cursor pagination.

        """
        if self.cursor:
            offset = self.cursor.offset
        else:
            offset = 0

        if self.cursor and self.cursor.position is not None:
            queryset = queryset.filter(id__gt=int(self.cursor.position))

        return queryset[: offset + self.page_size + 1]

    def get_page_ids(self, queryset: "QuerySet") -> list:
        """
        This method can be used in complex algorithms with annotations or aggregations.
        You can create two-step pipeline with data enrichment.

        """
        page = self._paginate(queryset)
        return list(page.only("id").values_list("id", flat=True))

    def get_page(self, queryset: "QuerySet") -> Page:
        """
        This method is most priority to simple get paginated data.

        """
        page = self._paginate(queryset)
        data = [x for x in page]
        return self.page_response(data)

    async def get_page_async(self, queryset: "QuerySet") -> Page:
        """
        This method is for using in async views. Unfortenatly Django not
        supports async filtering and slicing, and sync method is faster now.

        """
        page = self._paginate(queryset)
        data = [x async for x in page]
        return self.page_response(data)

    def page_response(self, data: list) -> Page:
        if len(data) > self.page_size:
            self.has_more_data = True
            data = data[:-1]
        else:
            self.has_more_data = False

        return Page(
            next=self.get_next_link(),
            previous=self.get_previous_link(),
            results=data,
        )

    def get_previous_link(self) -> str | None:
        if self.cursor:
            if self.cursor.offset < 2 * self.page_size:
                return self._encode_cursor(Cursor(offset=0, reverse=False, position=self.page_size))

            position = self.cursor.offset - self.page_size
            return self._encode_cursor(Cursor(offset=position, reverse=False, position=self.page_size))

    def get_next_link(self) -> str | None:
        if self.cursor:
            new_offset = self.cursor.offset
        else:
            new_offset = 0

        if self.has_more_data:
            return self._encode_cursor(
                Cursor(offset=new_offset + self.page_size, reverse=False, position=new_offset + self.page_size)
            )
