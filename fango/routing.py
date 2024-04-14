from typing import Callable

from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class FangoRouter(APIRouter):
    def get(self, *args, **kwargs) -> Callable:
        return super().get(*args, **kwargs, response_model_exclude_unset=True)

    def register(self, basename: str, klass: type) -> None:
        klass(self, basename)


action = FangoRouter()
