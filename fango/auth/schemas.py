from pydantic import BaseModel


class Token(BaseModel):
    access: str


class Credentials(BaseModel):
    email: str
    password: str
