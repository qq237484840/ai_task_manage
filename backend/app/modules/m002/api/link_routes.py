"""M002 挂接建议与门控端点（API-M002-007 / API-M002-008，契约 v0.4.4）。

- API-M002-007 `GET /api/v1/photos/{photo_id}/link-suggestions`（挂接建议查询 / 重试）
- API-M002-008 `GET /api/v1/photo-gates`（窗口级门控状态查询）

`CR-006` 子项 B：`API-M002-007` 响应 +`last_attempt`（消费 DATA-009 暴露 AI 失败原因；
成功 / 无记录 → `null`）。
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.core.ai.records import AICallRecord
from app.core.ai.service import CAPABILITY_PHOTO_LINK_SUGGEST
from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.errors import NotFoundError
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.schemas import (
    GateStatusDTO,
    LinkSuggestionItemOut,
    LinkSuggestionOut,
)
from app.modules.m002.services.gate_service import GateService
from app.modules.m002.services.link_service import LinkService
from app.shared.auth import AuthContext

_logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["M002 挂接建议/门控"])

#: DATA-009 关联检索键 —— `input_ref` 内的 `photo_id`（`input_ref` 为 JSON `TEXT`、**无独立列**
#: → 用 SQLite JSON1 `json_extract`；写入侧见 `app/core/ai/service.py::suggest_photo_links`）。
_JSON_PHOTO_ID = func.json_extract(AICallRecord.input_ref, "$.photo_id")


def _last_attempt(db: Session, photo_id: str) -> dict[str, Any] | None:
    """该照片**最近一次** `photo_link_suggest` 调用的失败留痕（`CR-006` 子项 B）。

    - 语义 = 「最近一次 AI 尝试」：**成功 → `None`**（不展示过期失败，避免误导用户重试）；
    - `error` 列为 JSON `TEXT`（`AIError.as_dict()` = `{code, message}`）→ 解析后原样透传；
      **脱敏 + 截断（≤200）由写入侧 `app/core/ai/errors.py` 单一来源保证，此处不重复实现**；
    - 任何读取异常（表不存在 / JSON 损坏 / 无 JSON1）→ `None` + warning，**不得影响主流程**。
    """
    try:
        recent = (
            db.query(AICallRecord)
            .filter(
                _JSON_PHOTO_ID == str(photo_id),
                AICallRecord.capability == CAPABILITY_PHOTO_LINK_SUGGEST,
            )
            .order_by(AICallRecord.created_at.desc(), AICallRecord.attempt.desc())
            .first()
        )
        if recent is None or recent.status != "error" or not recent.error:
            return None
        payload = json.loads(recent.error)
        if not isinstance(payload, dict):
            return None
        return {"code": payload.get("code"), "message": payload.get("message")}
    except Exception as exc:  # noqa: BLE001 - 留痕读取失败不得阻断主流程
        _logger.warning("读取 DATA-009 留痕失败（photo_id=%s）：%s", photo_id, exc)
        return None


@router.get("/photos/{photo_id}/link-suggestions", response_model=LinkSuggestionOut)
def get_link_suggestions(
    photo_id: str,
    retry: bool = Query(default=False, description="true = 对未挂接照片重试 AI 建议"),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    photo = PhotoRepository.get_by_id(db, ctx.family_id, photo_id)
    if photo is None or (ctx.is_student and ctx.student_id and photo.student_id != ctx.student_id):
        raise NotFoundError("照片不存在或无权访问")
    if retry:
        LinkService.suggest_for_photo(db, ctx.family_id, photo_id, settings=settings)
        db.commit()
        photo = PhotoRepository.get_by_id(db, ctx.family_id, photo_id)

    links = [link for link in LinkRepository.list_for_photo(db, photo.photo_id) if link.rejected_at is None]
    items: list[LinkSuggestionItemOut] = []
    for link in links:
        subject = None
        try:
            subject = TaskClient.get_group_subject(db, ctx.family_id, link.group_subject_id).subject
        except Exception:  # noqa: BLE001
            subject = None
        items.append(
            LinkSuggestionItemOut(
                link_id=link.link_id,
                group_subject_id=link.group_subject_id,
                subject=subject,
                confidence=link.confidence,
                source=link.source,
                suggested_at=link.created_at,
            )
        )
    # `CR-006` 子项 B：读取 DATA-009 暴露 AI 失败原因（检索键 = `input_ref.photo_id`）
    return LinkSuggestionOut(
        photo_id=photo.photo_id,
        status=photo.status,
        last_attempt=_last_attempt(db, photo.photo_id),
        suggestions=items,
    )


@router.get("/photo-gates", response_model=list[GateStatusDTO])
def list_photo_gates(
    student_id: UUID | None = Query(default=None),
    group_key: str | None = Query(default=None),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
):
    return GateService.list_gates(
        db,
        ctx.family_id,
        scope_student_id=ctx.student_id,
        student_id=str(student_id) if student_id else None,
        group_key=group_key,
    )
