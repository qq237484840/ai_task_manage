"""学校字典只读查询（DATA-011，全局共享公共字典，ADR-008）。

- 无 family_id：公共数据，登录即可查询（家庭隔离的限定例外）。
- 只读：不提供任何 create/update/delete 方法 —— 运行期无学校写路径。
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import School


class SchoolRepo:
    @staticmethod
    def get_by_id(session: Session, school_id: str) -> School | None:
        return session.get(School, school_id)

    @staticmethod
    def search(
        session: Session,
        *,
        stage: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[School], int]:
        conds = []
        if stage:
            conds.append(School.stage == stage)
        if keyword:
            conds.append(School.name.like(f"%{keyword}%"))
        stmt = select(School).where(*conds).order_by(School.name.asc(), School.school_id.asc())
        total = session.scalar(select(func.count()).select_from(School).where(*conds)) or 0
        rows = list(session.scalars(stmt.offset(offset).limit(limit)))
        return rows, total
