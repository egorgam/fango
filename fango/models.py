from typing import Any, List

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Model
from django.db.models.fields.related import (
    ForeignKey,
    ManyToManyField,
    ManyToOneRel,
    OneToOneField,
)
from fastapi import HTTPException
from pydantic import BaseModel

__all__ = ["PydanticAdapter"]


class PydanticAdapter(Model):
    """
    A base class for creating Django model instances from Pydantic schemas.

    """

    @classmethod
    @sync_to_async
    @transaction.atomic
    def from_schema(cls, schema_instance: BaseModel, pk: Any | None = None) -> Model:
        """
        Creates or updates a Django model instance from a Pydantic schema.

        """
        try:
            return _get_adapter_data(cls, schema_instance, pk=pk)
        except ObjectDoesNotExist as e:
            raise HTTPException(status_code=422, detail=str(e))

    class Meta:
        abstract = True


def _get_adapter_data(
    model: type[Model], schema_instance: BaseModel, pk: Any | None = None, rel: dict[str, Any] = {}
) -> Model:
    """
    Adapts data from a Pydantic schema instance to a Django model instance.

    """

    instance = model(pk=pk, **rel)
    handlers, rel_handlers = _get_fields_handlers(instance, model, schema_instance, pk)

    for handler, args in handlers:
        handler(*args)

    instance.save()

    for handler, args in rel_handlers:
        handler(*args)

    return instance


def _get_fields_handlers(
    instance: Model, model: type[Model], schema_instance: BaseModel, pk: Any | None = None
) -> tuple[list, list]:
    """
    Get handler for each field in schema.

    """
    handlers, rel_handlers = [], []

    for key, value in schema_instance:
        if isinstance(getattr(model, key), property):
            continue

        field_instance = model._meta.get_field(key)

        args = (field_instance, instance, key, value, pk)

        if isinstance(field_instance, ForeignKey):
            handlers.append((_create_relation_for_foreign_key, args))
        elif isinstance(field_instance, OneToOneField):
            handlers.append((_create_or_update_one_to_one_relation, args))
        elif isinstance(field_instance, ManyToOneRel):
            rel_handlers.append((_handle_many_to_one_relation, args))
        elif isinstance(field_instance, ManyToManyField):
            rel_handlers.append((_handle_many_to_many_relation, args))
        else:
            handlers.append((setattr, (instance, key, value)))

    return handlers, rel_handlers


def _create_relation_for_foreign_key(
    field_instance: ForeignKey, instance: Model, key: str, value: Any, pk=None
) -> None:
    """
    Assigns a related object or ID to a ForeignKey field in the instance of a model.

    """

    if isinstance(value, Model) or value is None:
        setattr(instance, key, value)

    elif isinstance(value, BaseModel):
        related_data = _get_adapter_data(field_instance.related_model, value, pk=pk)
        setattr(instance, key, related_data)
    else:
        related_instance = field_instance.related_model.objects.get(pk=value)
        setattr(instance, key, related_instance)


def _create_or_update_one_to_one_relation(
    field_instance: OneToOneField, instance: Model, key: str, value: Any, pk: Any
) -> None:
    """
    Creates or updates a OneToOne relationship for a model instance.

    """
    if isinstance(value, BaseModel):
        remote = {field_instance.field.get_attname(): pk}
        relation = _get_adapter_data(field_instance.related_model, value, pk=pk, rel=remote)
        relation.save()
        setattr(instance, key, relation)


def _process_many_to_one_relation_objects(field_instance: ManyToOneRel, value: Any, pk: Any) -> List[Model]:
    """
    Processes and creates objects for ManyToOne relations.

    """
    items = []
    for item in value:
        if isinstance(item, BaseModel):
            remote = {field_instance.remote_field.get_attname(): pk}
            relation = _get_adapter_data(
                field_instance.related_model,
                item,
                pk=pk,
                rel=remote,
            )
            items.append(relation)
        elif isinstance(item, Model):
            item.save()
            items.append(item)
    return items


def _update_many_to_one_relations(relation_set: Any, items: List[Model]) -> None:
    """
    Clears and updates the items in a ManyToOne relation set.

    """
    try:
        relation_set.clear()
        relation_set.set(items)
    except AttributeError:
        relation_set.all().delete()
        for item in items:
            item.save()


def _handle_many_to_one_relation(field_instance: ManyToOneRel, instance: Model, key: str, value: Any, pk: Any) -> None:
    """
    Manages ManyToOne relationship for model instances.

    """
    relation_set = getattr(instance, key)
    if value is None:
        relation_set.clear()
    elif isinstance(value, list):
        items = _process_many_to_one_relation_objects(field_instance, value, pk)
        _update_many_to_one_relations(relation_set, items)


def _handle_many_to_many_relation(
    field_instance: ManyToManyField, instance: Model, key: str, value: List[Any], pk=None
) -> None:
    """
    Manages the ManyToMany relations for a model instance.

    """
    if isinstance(value, list):
        relation_set = getattr(instance, key)
        relation_set.set(field_instance.related_model.objects.filter(pk__in=value))
