"""学生档案 Schema（API-M001-004~006）。

契约 DTO 约定（MODULE_API v0.1.1）：
StudentDTO = { student_id, name, grade_level, relation, school: { school_id, name, stage }, created_at, updated_at }
school 为档案必填关联的公共字典条目（ADR-008 / REQ-009）。
"""
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.m001.schemas.school import SchoolDTO


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    grade_level: str | None = Field(default=None, max_length=64)
    school_id: UUID
    relation: str | None = Field(default=None, max_length=16)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("学生姓名不能为空")
        return v


class StudentUpdate(BaseModel):
    """PATCH 语义：仅显式提供的字段生效（school_id 可改，校验同创建）。"""

    name: str | None = Field(default=None, min_length=1, max_length=32)
    grade_level: str | None = Field(default=None, max_length=64)
    school_id: UUID | None = None
    relation: str | None = Field(default=None, max_length=16)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("学生姓名不能为空")
        return v


class StudentDTO(BaseModel):
    student_id: UUID
    name: str
    grade_level: str | None
    relation: str | None
    school: SchoolDTO
    created_at: str
    updated_at: str
