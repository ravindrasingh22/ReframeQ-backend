from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    country: str = ''
    language: str = 'en'


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    role: str
    full_name: str
