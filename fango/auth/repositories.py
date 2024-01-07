from datetime import datetime, timedelta
from uuid import uuid4

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AbstractBaseUser
from fastapi import Request
from jose import jwt

from fango.auth.schemas import User

UserModel: type[AbstractBaseUser] = get_user_model()


def get_request(request: Request):
    request.META = {"REMOTE_ADDR": request.client.host}  # type: ignore
    return request


async def get_user_for_request_middleware(id: int) -> AbstractBaseUser | None:
    if user := await UserModel.objects.filter(id=id).afirst():
        return user


async def register_user(email: str, password: str) -> AbstractBaseUser:
    user = await UserModel.objects.acreate(
        email=email,
    )
    user.set_password(password)
    await user.asave(update_fields=["password"])
    return user


async def authenticate_user(request: Request, email: str, password: str):
    return await sync_to_async(authenticate)(request=request, email=email, password=password)


def create_access_token(user: AbstractBaseUser):
    pydantic_user = User.model_validate(user)

    if expires_delta := timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES):
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode = {
        "exp": expire,
        "jti": str(uuid4()),
        "user_id": pydantic_user.id,
        "token_type": "access",
    }
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded
