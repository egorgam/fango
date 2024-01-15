from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from jose import JWTError, jwt

User = get_user_model()


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


def get_user(request: "Request") -> "User":
    """
    Return User instance by token

    """
    payload = decode_token(request.headers["Authorization"])
    return User.objects.get(id=payload["user_id"])


async def get_user_async(request: "Request") -> "User":
    """
    Return User instance by token async

    """
    payload = decode_token(request.headers["Authorization"])
    return await User.objects.aget(id=payload["user_id"])


async def register_user(email: str, password: str) -> "User":
    user = await User.objects.acreate(
        email=email,
    )
    user.set_password(password)
    await user.asave(update_fields=["password"])
    return user


async def authenticate_user(request: Request, email: str, password: str):
    return await run_in_threadpool(authenticate, request=request, email=email, password=password)


def create_access_token(user: "User"):
    if expires_delta := timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES):
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode = {
        "exp": expire,
        "jti": str(uuid4()),
        "user_id": user.pk,
        "token_type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
