from types import MethodType
from typing import TypeVar

from django.db.models import Model
from pydantic import BaseModel

__all__ = ["MethodT", "BaseModelT", "ModelT"]

MethodT = TypeVar("MethodT", bound=MethodType)
BaseModelT = TypeVar("BaseModelT", bound=BaseModel)
ModelT = TypeVar("ModelT", bound=Model)
