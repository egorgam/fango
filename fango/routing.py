from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

public = APIRouter(prefix="/api")
private = APIRouter(prefix="/api", dependencies=[Depends(oauth2_scheme)])
