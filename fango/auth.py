__all__ = [
    "decode_token",
    "get_user",
    "get_user_async",
    "register_user",
    "authenticate_user",
    "create_access_token",
    "add_user_to_request_state",
]

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import User
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from fango.utils import run_async

UserModel: User = get_user_model()  # type: ignore


def decode_token(auth: str) -> dict:
    try:
        _, token = auth.split()
        return jwt.decode(
            token,
            settings.PUBLIC_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
    except (ValueError, UnicodeDecodeError, JWTError) as e:
        raise HTTPException(status_code=403, detail=str(e))


def get_user(request: Request) -> User:
    """
    Function returns User instance by token

    """
    payload = decode_token(request.headers["Authorization"])
    return UserModel.objects.only(*getattr(settings, "REQUEST_USER_FIELDS", ())).get(id=payload["user_id"])


async def get_user_async(request: Request) -> User:
    """
    Function returns User instance by token async

    """
    payload = decode_token(request.headers["Authorization"])
    return await UserModel.objects.only(*getattr(settings, "REQUEST_USER_FIELDS", ())).aget(id=payload["user_id"])


async def add_user_to_request_state(request: Request) -> None:
    """
    Function patches request.state to add user object.

    """
    request.state.user = await get_user_async(request)


async def register_user(email: str, password: str) -> User:
    """
    Function is creating User instance by token async.

    """
    user = await UserModel.objects.acreate(
        email=email,
    )
    user.set_password(password)
    await user.asave(update_fields=["password"])
    return user


async def authenticate_user(request: Request, email: str, password: str) -> User:
    """
    Function is authenticate user with django backend.

    """
    return await run_async(authenticate, request=request, email=email, password=password)


def create_access_token(user: User) -> str:
    """
    Function is creating access token.

    """
    if expires_delta := timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES):
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)

    to_encode = {
        "exp": expire,
        "jti": str(uuid4()),
        "user_id": user.pk,
        "token_type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
