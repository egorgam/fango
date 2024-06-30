import inspect
from types import FunctionType, MethodType
from typing import get_args

from django.contrib.auth.models import User
from django.db.models import Model
from django.utils.translation import gettext as _
from fastapi import HTTPException, Request

from fango.auth import add_user_to_request_state
from fango.routing import oauth2_scheme
from fango.utils import run_async, ttl_cache

__all__ = [
    "PermissionDependency",
    "ModelPermissions",
    "IsAuthenticated",
    "AllowAny",
]


class PermissionException(Exception):
    def __init__(self):
        super().__init__("Can't inspect endpoint model.")


class PermissionDependency:
    """
    Base class for permission dependency.

    """

    priority = 0
    use_cache = False

    @classmethod
    def __lt__(cls, permission: "PermissionDependency") -> bool:
        return cls.priority < permission.priority


class ModelPermissions(PermissionDependency):
    """
    Permission for checking django model permissions.

    It may be parametrized with model class, useful for @action.

    """

    priority = 1

    def __init__(self, model: Model | None = None) -> None:
        self.model: Model | None = model

    @classmethod
    async def dependency(cls, request: Request) -> None:
        await oauth2_scheme(request)
        await add_user_to_request_state(request)
        await _check_model_permissions(request)


class IsAuthenticated(PermissionDependency):
    """
    Permission for allowing all authenticated requests.

    """

    priority = 2

    @classmethod
    async def dependency(cls, request: Request) -> None:
        await oauth2_scheme(request)
        await add_user_to_request_state(request)


class AllowAny(PermissionDependency):
    """
    Permission for allowing all requests.

    """

    priority = 3

    @classmethod
    async def dependency(cls, request: Request) -> None:
        pass


@ttl_cache(10)
def _get_user_permissions(user: User) -> set[str]:
    """
    Function call user.get_all_permissions() in async context
    and caching to 10s.

    """
    return user.get_all_permissions()


def _get_permissions_mapping(request: Request):
    """
    Function for checking stored permission_mapping, or return default.

    """
    if state_stored := hasattr(request.state, "permissions_mapping"):
        assert isinstance(state_stored, list)
        return state_stored

    return {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


def _get_request_base_model(request: Request) -> Model:
    """
    Function return base model class for request.

    """
    endpoint = request.scope["endpoint"]

    if isinstance(endpoint, MethodType):
        model = endpoint.__self__.queryset.model

    elif isinstance(endpoint, FunctionType):
        if deps := [x for x in request.scope["route"].dependencies if isinstance(x, ModelPermissions)]:
            if not deps[0].model:
                raise PermissionError

            model = deps[0].model
        else:
            signature = inspect.signature(request.scope["route"].response_model)
            model = get_args(signature.parameters["results"].annotation)[0].model
    else:
        raise PermissionException

    return model


async def _check_model_permissions(request: Request, model=None) -> None:
    """
    Model Permissions check implementation.

    """

    model = _get_request_base_model(request)

    permissions_mapping = _get_permissions_mapping(request)
    user_permissions = await run_async(_get_user_permissions, request.state.user)

    if request.method in permissions_mapping:
        permissions = permissions_mapping[request.method]

        if not permissions:
            return

        for permission in permissions:
            if (
                permission % {"app_label": model._meta.app_label, "model_name": model._meta.model_name}
                in user_permissions
            ):
                return

    raise HTTPException(status_code=403, detail=_("You do not have permission to perform this action."))
