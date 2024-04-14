from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypedDict, TypeVar, get_args

from django.db.models import Manager
from pydantic import BaseModel, ConfigDict, field_validator
from typing_extensions import NotRequired

from fango.adapters.types import PK

__all__ = [
    "Cursor",
    "Page",
    "Entry",
    "ChoicesItem",
    "FormModel",
    "ActionClasses",
    "Multiselect",
    "CRUDAdapter",
    "UnlinkAdapter",
    "DBModel",
]

T = TypeVar("T")


@dataclass
class Cursor:
    offset: int
    reverse: int
    position: str | None


class Page(BaseModel, Generic[T]):
    next: str | None
    previous: str | None
    results: list[T]


class CRUDAdapter(BaseModel, Generic[T]):
    create: list[T] = []
    update: list[T] = []
    delete: list[PK]


class UnlinkAdapter(BaseModel, Generic[T]):
    unlink: list[PK]


class Entry(BaseModel, Generic[T]):
    title: str | None
    results: T


class ChoicesItem(BaseModel, Generic[T]):
    id: T
    name: str | None


class FormModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="before")
    def query_relation_manager(cls, value):
        if isinstance(value, Manager):
            return value.all()
        return value

    @field_validator("*", mode="after")
    def use_choices_label(cls, value, info):
        from fango.utils import get_choices_label

        annotation = cls.model_fields[info.field_name].annotation
        types = get_args(annotation)

        if value is not None:
            for type_ in types:
                if issubclass(type_, Enum):
                    return get_choices_label(type_, value)

                if metadata := getattr(type_, "__pydantic_generic_metadata__", None):
                    if metadata["origin"] is ChoicesItem:
                        return {"id": value, "name": get_choices_label(metadata["args"][0], value)}

        return value


class Multiselect(FormModel):
    id: int
    name: str | None = None


class DBModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ActionClasses(TypedDict):
    table: NotRequired[type[BaseModel]]
    retrieve: NotRequired[type[BaseModel]]
    update: NotRequired[type[BaseModel]]
    delete: NotRequired[type[BaseModel]]


class Token(BaseModel):
    access: str


class Credentials(BaseModel):
    email: str
    password: str
