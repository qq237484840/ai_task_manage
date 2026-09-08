"""学校字典只读路由（API-M001-012，DATA-011 全局共享公共字典，ADR-008）。

- 需登录（Bearer）但**不做家庭过滤**：公共数据。
- 只读：本 router 无 POST/PATCH/DELETE —— 运行期无学校写路径（405 由框架返回）。
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m001.repositories.school_repo import SchoolRepo
from app.modules.m001.schemas.school import SchoolDTO, SchoolPageResponse
from app.shared.auth import AuthContext

router = APIRouter(prefix="/schools", tags=["schools"])

_STAGES = ("primary", "junior", "senior")


@router.get("", response_model=SchoolPageResponse)
def list_schools(
    stage: str | None = Query(default=None, pattern="^(primary|junior|senior)$"),
    keyword: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    _: AuthContext = Depends(current_context),
):
    rows, total = SchoolRepo.search(
        session,
        stage=stage,
        keyword=keyword,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return SchoolPageResponse(
        items=[SchoolDTO(school_id=UUID(r.school_id), name=r.name, stage=r.stage) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
