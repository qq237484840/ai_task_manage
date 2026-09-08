"""学生档案读写（students）。强制 family_id 过滤 —— 裸查询即数据越权。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import School, Student

_UNSET = object()  # 区分"未提供"与"显式置空(None)"（PATCH 语义）

# 档案查询始终 join schools（StudentDTO.school 组装所需，公共字典 join 展示）
_STUDENT_SCHOOL = select(Student, School).join(School, Student.school_id == School.school_id)


class StudentRepo:
    @staticmethod
    def create(
        session: Session,
        *,
        family_id: str,
        name: str,
        grade_level: str | None,
        school_id: str,
        relation: str | None,
    ) -> Student:
        row = Student(
            family_id=family_id,
            name=name,
            grade_level=grade_level,
            school_id=school_id,
            relation=relation,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def _by_family(stmt, family_id: str):
        return stmt.where(Student.family_id == family_id)

    @staticmethod
    def get_with_school(session: Session, family_id: str, student_id: str) -> tuple[Student, School] | None:
        stmt = _STUDENT_SCHOOL.where(Student.student_id == student_id)
        stmt = StudentRepo._by_family(stmt, family_id)
        row = session.execute(stmt).first()
        return (row[0], row[1]) if row else None

    @staticmethod
    def list_with_school(session: Session, family_id: str) -> list[tuple[Student, School]]:
        stmt = _STUDENT_SCHOOL
        stmt = StudentRepo._by_family(stmt, family_id)
        stmt = stmt.order_by(Student.created_at.asc(), Student.student_id.asc())
        return [(s, sc) for s, sc in session.execute(stmt).all()]

    @staticmethod
    def get_names(session: Session, family_id: str, student_ids: list[str]) -> dict[str, str]:
        """按 id 批量取本家庭学生姓名（任务摘要展示用）。"""
        if not student_ids:
            return {}
        stmt = select(Student.student_id, Student.name).where(
            Student.family_id == family_id, Student.student_id.in_(student_ids)
        )
        return dict(session.execute(stmt).all())

    @staticmethod
    def update(
        session: Session,
        row: Student,
        *,
        name: str | object = _UNSET,
        grade_level: str | None | object = _UNSET,
        school_id: str | object = _UNSET,
        relation: str | None | object = _UNSET,
    ) -> None:
        if name is not _UNSET:
            row.name = name
        if grade_level is not _UNSET:
            row.grade_level = grade_level
        if school_id is not _UNSET:
            row.school_id = school_id
        if relation is not _UNSET:
            row.relation = relation
