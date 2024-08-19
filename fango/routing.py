from typing import Callable

from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class FangoRouter(APIRouter):
    viewsets = []

    def get(self, *args, **kwargs) -> Callable:
        response_model_exclude_unset = kwargs.pop("response_model_exclude_unset", True)
        return super().get(*args, **kwargs, response_model_exclude_unset=response_model_exclude_unset)

    def register(self, basename: str, klass: type) -> None:
        self.viewsets.append(klass(self, basename))


action = FangoRouter()
