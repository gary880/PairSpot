from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr


class RegisterInitiateRequest(BaseModel):
    email_a: EmailStr
    email_b: EmailStr
    couple_name: str
    anniversary_date: date | None = None


class RegisterInitiateResponse(BaseModel):
    couple_id: str
    message: str


class RegisterVerifyRequest(BaseModel):
    token: str


class RegisterVerifyResponse(BaseModel):
    email: str
    verified: bool
    both_verified: bool


class RegisterCompleteRequest(BaseModel):
    couple_id: str
    password_a: str
    password_b: str
    display_name_a: str
    display_name_b: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
