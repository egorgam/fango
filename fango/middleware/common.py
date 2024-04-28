from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.middleware.common import CommonMiddleware


class FangoCommonMiddleware(CommonMiddleware):
    """
    Redirect with slash all routes.

    For other things is uses CommonMiddleware defults.

    """

    def should_redirect_with_slash(self, request: ASGIRequest) -> bool:
        """
        Append slash to all routes if APPEND_SLASH is True.

        """

        if settings.APPEND_SLASH and not request.path.endswith("/"):
            return True
        else:
            return False
