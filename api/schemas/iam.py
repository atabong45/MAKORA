"""
MODULE : api/schemas/iam.py
DESCRIPTION : Schémas Pydantic v2 pour le domaine IAM.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator
import re


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mot de passe trop court (min 8 caractères)")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mot de passe trop court (min 8 caractères)")
        return v


class RoleBase(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: str | None = None
    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class UserMe(UserBase):
    roles: list[str] = []


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    role: str = "gestionnaire"

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Username invalide (alphanumérique + _, 3-50 chars)")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    roles: list[RoleBase] = []


class SessionInfo(BaseModel):
    id: UUID
    ip_address: str | None
    user_agent: str | None
    expires_at: datetime
    created_at: datetime
    model_config = {"from_attributes": True}


class RoleAssign(BaseModel):
    role_id: UUID


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    resource: str
    action: str
    description: str | None = None
    model_config = {"from_attributes": True}


class RoleDetail(RoleBase):
    permissions: list[PermissionResponse] = []
