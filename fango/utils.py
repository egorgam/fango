import asyncio

from django.conf import settings


def reverse_ordering(ordering_tuple: tuple[str, ...]) -> tuple[str, ...]:
    """
    Function returns ordering tuple with reversed keys.

    """
    return tuple(("-" + item) if not item.startswith("-") else item[1:] for item in ordering_tuple)


def replace_proto(url: str | None) -> str | None:
    """
    Function is replace http to https, it's useful behind reverse proxy.

    """
    if url and not settings.DEBUG:
        return url.replace("http://", "https://")
    return url


class async_cached_property:
    """
    Async cached property.

    """

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
