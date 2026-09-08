"""学校字典 Schema（API-M001-012，DATA-011 公共只读）。"""

from uuid import UUID

from pydantic import BaseModel

from app.modules.m001.schemas.common import PageMeta


class SchoolDTO(BaseModel):
    school_id: UUID
    name: str
    stage: str


class SchoolPageResponse(PageMeta):
    items: list[SchoolDTO]
