from pydantic import BaseModel, validator


class UserItem(BaseModel):
    username: str
    email: str
    test: str
    username_with_email: str | None = None

    @validator("username_with_email", pre=True, always=True)
    def combine_username_and_email(cls, v, values):
        return f"{values['username']}<{values['email']}>"
