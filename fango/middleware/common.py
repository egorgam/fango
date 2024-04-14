from functools import lru_cache

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.middleware.common import CommonMiddleware
from django.urls import is_valid_path


@lru_cache
def get_routes_patch(request: ASGIRequest) -> tuple[str, ...]:
    """
    Cache all FastAPI app patches.

    """
    return tuple([x.path.strip("/") for x in request.scope["app"].router.routes])


class FangoCommonMiddleware(CommonMiddleware):
    """
    Redirect with slash all routes.

    For other features use CommonMiddleware defults.

    """

    def should_redirect_with_slash(self, request: ASGIRequest) -> bool:
        """
        Append slash to all routes if APPEND_SLASH is True.

        """

        if (
            settings.APPEND_SLASH
            and not request.path.endswith("/")
            or is_valid_path(f"{request.path}/")
            and not request.path.endswith("/")
        ):
            return True
        else:
            return False
