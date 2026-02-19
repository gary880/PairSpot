from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, field_validator


class RegisterInitiateRequest(BaseModel):
    email_a: EmailStr
    email_b: EmailStr
    couple_name: str
    anniversary_date: date | None = None

    @field_validator("couple_name")
    @classmethod
    def couple_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("couple_name cannot be empty")
        return v


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

    @field_validator("password_a", "password_b")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("display_name_a", "display_name_b")
    @classmethod
    def display_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name cannot be empty")
        return v


class RegisterCompleteResponse(BaseModel):
    couple_id: str
    message: str


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


class AppleLoginRequest(BaseModel):
    identity_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
