from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: int
    email: str = EmailStr()

    class Config:
        from_attributes = True


class UserInDB(User):
    password: str


class Token(BaseModel):
    access: str


class Credentials(BaseModel):
    email: str
    password: str
