from dataclasses import dataclass
from typing import Generic, TypedDict, TypeVar, get_args

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import IntegerChoices, Manager, Model
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing_extensions import NotRequired

from fango.adapters.types import PK

__all__ = [
    "Cursor",
    "Page",
    "Entry",
    "ChoicesItem",
    "FangoModel",
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
    title: str | None = None
    status: str | None = None
    results: T


class ChoicesItem(BaseModel, Generic[T]):
    id: T
    name: str | None


class FangoModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="before")
    def validate_relation(cls, value):
        if isinstance(value, Manager):
            return value.all()
        return value

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data):
        from fango.utils import get_choices_label

        for key, field in cls.model_fields.items():
            if isinstance(data, dict):
                if value := data.get(key, field.default):
                    data[key] = value

                for type_ in get_args(field.annotation):
                    if issubclass(type_, IntegerChoices):
                        data[key] = get_choices_label(type_, value or field.default)  # type: ignore

                    elif metadata := getattr(type_, "__pydantic_generic_metadata__", None):
                        if value is not None and metadata["origin"] is ChoicesItem:
                            data[key] = {"id": value, "name": get_choices_label(metadata["args"][0], value)}

            elif isinstance(data, Model):
                try:
                    value = getattr(data, key)
                except ObjectDoesNotExist:
                    value = None

                if not value:
                    setattr(data, key, value)

                for type_ in get_args(field.annotation):
                    if issubclass(type_, IntegerChoices):
                        setattr(data, key, get_choices_label(type_, value or field.default))  # type: ignore

                    elif metadata := getattr(type_, "__pydantic_generic_metadata__", None):
                        if value is not None and metadata["origin"] is ChoicesItem:
                            setattr(data, key, {"id": value, "name": get_choices_label(metadata["args"][0], value)})

        return data


class Multiselect(FangoModel):
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
