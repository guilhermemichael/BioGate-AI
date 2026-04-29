from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization_name: str | None = Field(default=None, min_length=3, max_length=160)
    organization_slug: str | None = Field(default=None, min_length=3, max_length=100)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("organization_name", "organization_slug")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization_slug: str | None = Field(default=None, min_length=3, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("organization_slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    revoke_all: bool = False


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan: str
    is_active: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    full_name: str
    email: EmailStr
    role: str
    status: str
    failed_login_attempts: int
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime
    permissions: list[str] = Field(default_factory=list)
    organization: OrganizationResponse | None = None


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    access_token_expires_in: int


class AuthResponse(AccessTokenResponse):
    refresh_token: str
    refresh_token_expires_in: int
    session_id: str
    user: UserResponse


class ProtectedRouteResponse(BaseModel):
    message: str
    user: UserResponse


class SessionResponse(BaseModel):
    id: str
    user_id: str
    organization_id: str
    rotation_counter: int
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    revoked_reason: str | None
    is_current: bool


class SessionsListResponse(BaseModel):
    items: list[SessionResponse]


class TrustedDeviceResponse(BaseModel):
    id: str
    user_id: str
    organization_id: str
    fingerprint_preview: str | None
    display_name: str | None
    is_trusted: bool
    first_seen_at: datetime
    last_seen_at: datetime
    last_ip_address: str | None
    last_user_agent: str | None


class TrustedDevicesListResponse(BaseModel):
    items: list[TrustedDeviceResponse]
