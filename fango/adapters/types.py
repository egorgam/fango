import typing
from datetime import date, datetime, time
from uuid import UUID

from pydantic import Field

PK = int | UUID


def _check(type_: type, annotation) -> bool:
    return annotation == type_ or type_ in typing.get_args(annotation)


def is_date(field: Field) -> bool:
    return _check(date, field.annotation)


def is_datetime(field: Field) -> bool:
    return _check(datetime, field.annotation)


def is_time(field: Field) -> bool:
    return _check(time, field.annotation)


def is_bool(field: Field) -> bool:
    return _check(bool, field.annotation)


def is_uuid(field: Field) -> bool:
    return _check(UUID, field.annotation)


def is_numeric(field: Field) -> bool:
    return any([_check(type_, field.annotation) for type_ in (int, float, complex)])


def is_list(field: Field) -> bool:
    return _check(list, field.annotation)
