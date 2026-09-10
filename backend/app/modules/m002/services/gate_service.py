"""窗口级门控服务（API-M002-008 / 009 前置校验）。

门控语义（ADR-013 / 契约 §门控）：某归属窗口（按 group_key）下**全部照片挂接确认后**
才允许生成/重跑完成分析；否则返回「待复核 N 张」。
- 窗口成员 = 至少有一条有效挂接（未判无效）且归属该窗口的照片；AI 失败保持 unassigned
  的照片不属于任何窗口（不阻断，需手工挂接）。
- pending = 窗口内尚无确认挂接的照片数。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.m002.clients.task_client import GroupSubjectRef, TaskClient
from app.modules.m002.domain.enums import PhotoStatus
from app.modules.m002.domain.errors import M001UnavailableError, NotFoundError
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.schemas import GateStatusDTO

_LINKED_STATUSES = (PhotoStatus.SUGGESTED, PhotoStatus.ASSIGNED, PhotoStatus.REJECTED)


class GateService:
    @staticmethod
    def _scoped_student(student_id: str | None, scope_student_id: str | None) -> str | None:
        if scope_student_id is not None:
            if student_id is not None and str(student_id) != str(scope_student_id):
                raise NotFoundError("学生档案不存在或无权访问")
            return str(scope_student_id)
        return str(student_id) if student_id else None

    @staticmethod
    def list_gates(
        session: Session,
        family_id: str,
        *,
        scope_student_id: str | None = None,
        student_id: str | None = None,
        group_key: str | None = None,
    ) -> list[GateStatusDTO]:
        sid = GateService._scoped_student(student_id, scope_student_id)
        rows, _ = PhotoRepository.list_photos(
            session,
            family_id,
            student_id=sid,
            statuses=_LINKED_STATUSES,
            limit=100_000,
        )
        photo_ids = [p.photo_id for p in rows]
        active_links = LinkRepository.list_active_for_photos(session, photo_ids)
        if not active_links:
            return []

        ref_cache: dict[str, GroupSubjectRef] = {}

        def resolve(gs_id: str) -> GroupSubjectRef:
            if gs_id not in ref_cache:
                ref_cache[gs_id] = TaskClient.get_group_subject(session, family_id, gs_id)
            return ref_cache[gs_id]

        windows: dict[str, dict] = {}
        for link in active_links:
            ref = resolve(link.group_subject_id)
            bucket = windows.setdefault(
                ref.group_key, {"window_type": ref.window_type, "total": set(), "pending": set()}
            )
            bucket["total"].add(link.photo_id)
            if link.confirmed_at is None:
                bucket["pending"].add(link.photo_id)

        result: list[GateStatusDTO] = []
        for key, bucket in windows.items():
            if group_key is not None and key != group_key:
                continue
            total = len(bucket["total"])
            pending = len(bucket["pending"])
            result.append(
                GateStatusDTO(
                    group_key=key,
                    window_type=bucket["window_type"],
                    total_photos=total,
                    pending_photos=pending,
                    satisfied=pending == 0,
                )
            )
        result.sort(key=lambda g: g.group_key)
        return result

    @staticmethod
    def get_gate(
        session: Session,
        family_id: str,
        *,
        student_id: str | None,
        group_key: str,
        scope_student_id: str | None = None,
    ) -> GateStatusDTO:
        """单窗口门控；窗口无照片 → 视为满足（total=0）。"""
        gates = GateService.list_gates(
            session,
            family_id,
            scope_student_id=scope_student_id,
            student_id=student_id,
            group_key=group_key,
        )
        if gates:
            return gates[0]
        return GateStatusDTO(
            group_key=group_key,
            window_type="",
            total_photos=0,
            pending_photos=0,
            satisfied=True,
        )


__all__ = ["GateService", "M001UnavailableError"]
