import asyncio

from django.conf import settings
from jose import JWTError, jwt
from starlette.authentication import AuthenticationBackend, AuthenticationError

from fango.auth.repositories import get_user_for_request_middleware


class BearerTokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, request) -> tuple[str, asyncio.Task] | None:
        if "Authorization" not in request.headers:
            return

        auth = request.headers["Authorization"]
        try:
            scheme, token = auth.split()
            if scheme != "Bearer":
                return
            decoded = jwt.decode(
                token,
                settings.PUBLIC_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_aud": False},
            )
        except (ValueError, UnicodeDecodeError, JWTError):
            raise AuthenticationError("Invalid JWT Token.")

        user = asyncio.ensure_future(get_user_for_request_middleware(decoded["user_id"]))

        return auth, user
