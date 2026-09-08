"""家庭空间服务：学生档案（含学校字典关联）与内部接口 FamilySpaceService。

分层：Service 承载业务规则（归属校验、school_id 存在性）；Repository 承担查询。
学生姓名等未成年人信息不写入日志（audit 仅记 student_id）。
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.modules.m001.models.orm import School, Student
from app.modules.m001.repositories.school_repo import SchoolRepo
from app.modules.m001.repositories.student_repo import StudentRepo
from app.modules.m001.schemas.school import SchoolDTO
from app.modules.m001.schemas.student import StudentCreate, StudentDTO, StudentUpdate
from app.shared.exceptions import NotFoundError, PermissionDeniedError, ValidationAppError


def school_dto(school: School) -> SchoolDTO:
    return SchoolDTO(school_id=UUID(school.school_id), name=school.name, stage=school.stage)


def student_dto(student: Student, school: School) -> StudentDTO:
    return StudentDTO(
        student_id=UUID(student.student_id),
        name=student.name,
        grade_level=student.grade_level,
        relation=student.relation,
        school=school_dto(school),
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


class StudentService:
    """学生档案 REST 业务（API-M001-004~006）。"""

    @staticmethod
    def _require_school(session: Session, school_id: str) -> None:
        if SchoolRepo.get_by_id(session, school_id) is None:
            raise ValidationAppError("school_id 不存在于学校字典")

    @staticmethod
    def create(session: Session, family_id: str, data: StudentCreate) -> StudentDTO:
        school_id = str(data.school_id)
        StudentService._require_school(session, school_id)
        student = StudentRepo.create(
            session,
            family_id=family_id,
            name=data.name,
            grade_level=data.grade_level,
            school_id=school_id,
            relation=data.relation,
        )
        audit_event("student_created", family_id=family_id, student_id=student.student_id)
        school = SchoolRepo.get_by_id(session, school_id)
        assert school is not None
        return student_dto(student, school)

    @staticmethod
    def list(session: Session, family_id: str, *, scope_student_id: str | None = None) -> list[StudentDTO]:
        """档案列表：family 主体=本家全部；student 主体（scope_student_id）=仅本人。"""
        if scope_student_id is not None:
            result = StudentRepo.get_with_school(session, family_id, scope_student_id)
            return [student_dto(s, sc) for s, sc in [result]] if result else []
        return [student_dto(s, sc) for s, sc in StudentRepo.list_with_school(session, family_id)]

    @staticmethod
    def update(
        session: Session,
        family_id: str,
        student_id: str,
        data: StudentUpdate,
        *,
        scope_student_id: str | None = None,
    ) -> StudentDTO:
        if scope_student_id is not None and student_id != scope_student_id:
            raise NotFoundError("学生档案不存在")  # student 主体改他人 = 不可见（404 防探测）
        result = StudentRepo.get_with_school(session, family_id, student_id)
        if result is None:
            raise NotFoundError("学生档案不存在")  # 跨家庭/不存在统一 404（不泄露存在性）
        student, _ = result
        fields: dict = {}
        for key in ("name", "grade_level", "relation"):
            if key in data.model_fields_set:
                fields[key] = getattr(data, key)
        if "school_id" in data.model_fields_set and data.school_id is not None:
            StudentService._require_school(session, str(data.school_id))
            fields["school_id"] = str(data.school_id)
        if fields:
            StudentRepo.update(session, student, **fields)
            audit_event("student_updated", family_id=family_id, student_id=student.student_id)
        school = SchoolRepo.get_by_id(session, student.school_id)
        assert school is not None
        return student_dto(student, school)


class FamilySpaceService:
    """内部服务接口（进程内，供 M002/M004/M005/M007 引用；契约见 MODULE_API）。

    所有方法必须携带 family_id 上下文；越权/不存在抛 PermissionDenied（内部语义统一 403，
    与 REST 对外 404 防探测语义区分）。
    """

    @staticmethod
    def get_student(session: Session, family_id: str, student_id: str) -> StudentDTO:
        result = StudentRepo.get_with_school(session, family_id, student_id)
        if result is None:
            raise PermissionDeniedError("学生档案不存在或无权访问")
        student, school = result
        return student_dto(student, school)
