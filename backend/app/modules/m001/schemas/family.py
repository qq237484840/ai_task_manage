"""家庭认证 Schema（API-M001-001~003）。"""

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("密码至少 8 位")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
        raise ValueError("密码必须同时包含字母与数字")
    return v


class FamilyRegister(BaseModel):
    login_name: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=32)

    _check_password = field_validator("password")(_validate_password_strength)


class FamilyLogin(BaseModel):
    login_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class FamilyRegisterResponse(BaseModel):
    family_id: UUID
    display_name: str


class LoginResponse(BaseModel):
    token: str
    expires_at: str
