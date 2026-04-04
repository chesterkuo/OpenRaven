"""Pydantic models for auth data."""

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    email_verified: bool = False


class TenantResponse(BaseModel):
    id: str
    name: str
    storage_quota_mb: int = 500


class AuthContext(BaseModel):
    user_id: str
    tenant_id: str
    email: str


class AuthMeResponse(BaseModel):
    user: UserResponse
    tenant: TenantResponse


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    password: str
