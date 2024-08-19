import asyncio
import types
from functools import wraps
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Choices, Field, ForeignObjectRel, Model
from django.db.models.enums import ChoicesMeta
from fastapi.concurrency import run_in_threadpool

from fango.generics import MethodT
from fango.routing import FangoRouter
from fango.schemas import ChoicesItem

__all__ = [
    "ttl_cache",
    "reverse_ordering",
    "replace_proto",
    "run_async",
    "run_sync",
    "get_choices_as_data",
    "copy_instance_method",
    "get_choices_label",
    "get_model_field_safe",
    "generate_tags_metadata",
]


def ttl_cache(ttl=None) -> Any:
    """
    Decorator for TTL caching.

    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapped(*args, **kwargs) -> Callable:
            key = "ttl_cache_key_{}_{}".format(func.__name__, hash(args) + hash(frozenset(kwargs.items())))
            result = cache.get(key)
            if result is not None:
                return result
            else:
                result = func(*args, **kwargs)
            cache.set(key, result, timeout=ttl)
            return result

        return wrapped

    return decorator


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


async def run_async(func, *args, **kwargs) -> Any:
    """
    Funcion is a wrapper to run sync code in async context using thread pool.

    """
    if iscoroutinefunction(func):
        raise Exception("Can't run coroutine in thread!")

    return await run_in_threadpool(func, *args, **kwargs)


def run_sync(func) -> Any:
    """
    Funcion is a wrapper to run async code in sync context.

    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(func)


def get_choices_as_data(choices_class: ChoicesMeta) -> list[ChoicesItem]:
    """
    Function for get choices enum as key value data.

    """
    return [ChoicesItem.model_validate({"id": value, "name": label}) for value, label in choices_class.choices]


def copy_instance_method(method: MethodT) -> MethodT:
    """
    Function make a copy of class method with copy of method function.

    """
    return types.MethodType(
        types.FunctionType(
            method.__code__,  # type: ignore
            method.__globals__,  # type: ignore
            name=method.__name__,
            argdefs=method.__defaults__,
            closure=method.__closure__,
        ),
        method.__self__,
    )


def get_choices_label(enum: type[Choices], value: int) -> str | None:
    """
    Function returns choices text.

    """
    choices_dict = dict(enum.choices)
    return choices_dict.get(value)


def get_model_field_safe(model: type[Model], field_name: str) -> "Field | ForeignObjectRel | GenericForeignKey":
    """
    Function returns model field by name.
    If field is FK rel without related_name, this attr will be processed correctly.

    """
    try:
        return model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return model._meta.get_field(field_name.removesuffix("_set"))


def generate_tags_metadata(router: FangoRouter) -> list[dict]:
    """
    Function retuns list of dicts with openapi metadata tags name and description for router.

    """
    return [
        {"name": viewset._basename, "description": viewset.__doc__ or viewset.queryset.model._meta.verbose_name}
        for viewset in router.viewsets
    ]
