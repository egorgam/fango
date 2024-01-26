__all__ = [
    "CHECK_MODEL_PERMISSIONS",
    "ALLOW_ANY",
]

import typing

if typing.TYPE_CHECKING:
    from django.contrib.auth.models import User

from fastapi import Depends, HTTPException, Request

from fango.utils import orm_async, ttl_cache


@ttl_cache(10)
async def _get_user_permissions(user: "User") -> set[str]:
    """
    Function call user.get_all_permissions() in async context
    and caching to 10s.

    """
    return await orm_async(user.get_all_permissions)


def _get_permissions_mapping(request: "Request"):
    """
    Function for checking stored permission_mapping, or return default.

    """
    if state_stored := hasattr(request.app.state, "permissions_mapping"):
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


async def _check_model_permissions(request: "Request") -> None:
    """
    Model Permissions check implementation.

    """
    model = request.scope["endpoint"].__self__.queryset.model
    permissions_mapping = _get_permissions_mapping(request)
    user_permissions = await _get_user_permissions(request.app.state.user)

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

    raise HTTPException(status_code=405, detail="Method not allowed.")


async def _allow_any() -> None:
    """
    Permission for allowing all requests.

    """


CHECK_MODEL_PERMISSIONS = Depends(_check_model_permissions, use_cache=False)
ALLOW_ANY = Depends(_allow_any, use_cache=False)