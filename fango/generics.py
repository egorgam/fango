__all__ = ["MethodT"]

from types import MethodType
from typing import TypeVar

from pydantic import BaseModel

MethodT = TypeVar("MethodT", bound=MethodType)
BaseModelT = TypeVar("BaseModelT", bound=BaseModel)
