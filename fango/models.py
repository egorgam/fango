from datetime import datetime
from uuid import UUID

from django.db.models import Model
from pydantic import BaseModel


class PydanticAdapter(Model):
    @classmethod
    async def from_schema(cls, schema: BaseModel, pk=None):
        """
        Method builds Django ORM model instance from pydantic model instance.

        """
        result = {"id": pk, "created": datetime.now()}
        data = schema.model_dump()

        for field in schema.model_fields:
            orm_descriptior = getattr(cls, field)
            value = data[field]

            if orm_descriptior.field.is_relation:
                if value is None:
                    result[field] = None
                elif isinstance(value, int | UUID):
                    if field.endswith("_id"):
                        result[field] = value
                    else:
                        result[field] = await orm_descriptior.field.related_model.objects.filter(pk=value).afirst()
                elif isinstance(value, dict):
                    result[field] = orm_descriptior.field.related_model(**value)
                elif isinstance(value, list):
                    if len(value):
                        raise NotImplementedError
                else:
                    raise NotImplementedError
            else:
                result[field] = value

        return cls(**result)

    class Meta:
        abstract = True
