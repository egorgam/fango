from django.contrib.auth.models import User
from django.db.models import Value
from fastapi import APIRouter

from core.models.user import UserItem

router = APIRouter()


@router.get("/api/v1/users/", response_model=list[UserItem])
async def read_users(username: str | None = None) -> list[UserItem]:
    qs = User.objects.annotate(test=Value("TEST"))

    if username:
        qs = qs.filter(username__istartswith=username)

    users = [user async for user in qs]

    user_items = [UserItem(username=user.username, email=user.email, test=getattr(user, "test")) for user in users]
    return user_items
