"""学生子账号 Schema（ACR-001 新增：开通/停用/改密/学生登录/主体信息）。"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StudentAccountCreate(BaseModel):
    """家长为学生档案开通子账号。login_name 全局唯一（学生登录命名空间）。"""

    login_name: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class StudentAccountUpdate(BaseModel):
    """家长停用/启用/改密（PATCH：仅显式字段生效，至少提供其一）。"""

    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("status")
    @classmethod
    def strip_status(cls, v: str | None) -> str | None:
        return v.lower() if v else v


class StudentAccountDTO(BaseModel):
    student_id: UUID
    login_name: str
    status: str  # active | disabled
    created_at: str
    updated_at: str


class StudentLogin(BaseModel):
    login_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class StudentLoginResponse(BaseModel):
    token: str
    expires_at: str
    subject_type: str = "student"
    student_id: UUID
    student_name: str


class StudentAccountCreateResponse(StudentAccountDTO):
    """开通/更新学生子账号响应（ACR-001）。password_warning 在学生弱口令时提示。"""

    password_warning: str | None = None
