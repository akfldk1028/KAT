from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    user_id: str
    password: str
    name: str

class UserLogin(BaseModel):
    user_id: str
    password: str

class TokenData(BaseModel):
    token: str

class AuthResponse(BaseModel):
    data: Optional[TokenData] = None
    msg: str
