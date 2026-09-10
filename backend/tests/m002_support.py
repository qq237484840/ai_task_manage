"""M002 v0.4.0 测试支撑：M001 契约桩网关 + Mock AI + 图片合成 + fixtures。

- FakeGateway：内存态聚合对象/学科子任务，避免依赖 M001 内部数据构造；既有方法
  （student_exists/get_task/mark_in_progress）回退到真实 M001，保证双主体语义一致。
- 通过 set_gateway / set_ai_client / set_scheduler 注入，测试结束复位。
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from app.modules.m002.clients.ai_client import MockAiClient, set_ai_client
from app.modules.m002.clients.task_client import (
    DefaultM001Gateway,
    GroupSubjectRef,
    TaskGroupRef,
    set_gateway,
)
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.errors import LinkTargetMissingError
from app.modules.m002.services.suggestion_scheduler import set_scheduler


class FakeGateway:
    """M001 聚合层契约桩（可注入 port；不复制 M001 业务逻辑）。"""

    def __init__(self) -> None:
        self._real = DefaultM001Gateway()
        self.groups: dict[str, TaskGroupRef] = {}
        self.group_by_key: dict[tuple[str, str, str], str] = {}
        self.in_progress_calls: list[str] = []
        self.conclusions: list[dict[str, Any]] = []
        self.tasks: dict[str, Any] = {}

    # —— 测试装配 ——
    def add_task(self, task_id: str, student_id: str) -> None:
        self.tasks[task_id] = SimpleNamespace(task_id=task_id, student_id=student_id)

    def register_group(
        self,
        *,
        student_id: str,
        group_key: str,
        window_type: str = "day",
        category: str = "homework",
        window_task_id: str | None = None,
        task_status: str = "published",
        subjects: list[tuple[str, str]] | None = None,
        group_id: str | None = None,
        display_name: str | None = None,
    ) -> TaskGroupRef:
        gid = group_id or str(uuid4())
        subs = [
            GroupSubjectRef(
                group_subject_id=gsid,
                subject=subject,
                student_id=student_id,
                group_id=gid,
                group_key=group_key,
                window_type=window_type,
                category=category,
                window_task_id=window_task_id,
                task_status=task_status,
            )
            for gsid, subject in (subjects or [])
        ]
        group = TaskGroupRef(
            group_id=gid,
            student_id=student_id,
            category=category,
            group_key=group_key,
            window_type=window_type,
            display_name=display_name or group_key,
            window_task_id=window_task_id,
            task_status=task_status,
            subjects=subs,
        )
        self.groups[gid] = group
        self.group_by_key[(student_id, category, group_key)] = gid
        return group

    # —— M001Gateway 协议 ——
    def student_exists(self, session: Session, family_id: str, student_id: str) -> bool:
        return self._real.student_exists(session, family_id, student_id)

    def get_task(self, session: Session, family_id: str, task_id: str) -> Any:
        if task_id in self.tasks:
            return self.tasks[task_id]
        return self._real.get_task(session, family_id, task_id)

    def mark_in_progress(self, session: Session, family_id: str, task_id: str) -> tuple[str, str]:
        self.in_progress_calls.append(task_id)
        if task_id in self.tasks:
            return task_id, "in_progress"
        try:
            return self._real.mark_in_progress(session, family_id, task_id)
        except Exception:  # noqa: BLE001 - 桩场景任务不存在时仅记录
            return task_id, "in_progress"

    def list_groups(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        group_key: str | None = None,
    ) -> list[TaskGroupRef]:
        out = []
        for group in self.groups.values():
            if student_id and str(group.student_id) != str(student_id):
                continue
            if group_key and group.group_key != group_key:
                continue
            out.append(group)
        return out

    def get_group(self, session: Session, family_id: str, group_id: str) -> TaskGroupRef:
        group = self.groups.get(group_id)
        if group is None:
            raise LinkTargetMissingError("聚合对象不存在")
        return group

    def ensure_group(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str,
        category: str,
        belong_date: str,
    ) -> TaskGroupRef:
        gid = self.group_by_key.get((student_id, category, belong_date))
        if gid:
            return self.groups[gid]
        return self.register_group(
            student_id=student_id, group_key=belong_date, category=category
        )

    def commit_conclusion(
        self,
        session: Session,
        family_id: str,
        *,
        group_subject_id: str,
        conclusion: str,
        evidence_photo_ids: list[str],
        confidence: float | None,
        status: str,
    ) -> Any:
        self.conclusions.append(
            {
                "group_subject_id": group_subject_id,
                "conclusion": conclusion,
                "evidence_photo_ids": list(evidence_photo_ids),
                "confidence": confidence,
                "status": status,
            }
        )
        return SimpleNamespace(
            group_subject_id=group_subject_id, conclusion=conclusion, conclusion_status=status
        )

    def get_group_subject(
        self, session: Session, family_id: str, group_subject_id: str
    ) -> GroupSubjectRef:
        for group in self.groups.values():
            for subject in group.subjects:
                if subject.group_subject_id == group_subject_id:
                    return subject
        raise LinkTargetMissingError("聚合学科子任务不存在或无权访问")


@dataclass
class M002Infra:
    gateway: FakeGateway
    ai: MockAiClient
    _resets: list = field(default_factory=list)


@pytest.fixture
def m002_image_settings(tmp_path, client):
    """把图片存储根重定向到临时目录（避免污染 backend/data/images）。"""
    s = M002Settings(image_store_root=str(tmp_path / "images"))
    client.app.dependency_overrides[get_m002_settings] = lambda: s
    yield s
    client.app.dependency_overrides.pop(get_m002_settings, None)


@pytest.fixture
def m002_infra():
    """注入契约桩网关 + Mock AI + 内联调度；用例内可自由配置。"""
    gateway = FakeGateway()
    ai = MockAiClient()
    set_gateway(gateway)
    set_ai_client(ai)
    set_scheduler(lambda runner: runner())
    yield M002Infra(gateway=gateway, ai=ai)
    set_gateway(None)
    set_ai_client(None)
    set_scheduler(None)


def make_task_row(
    factory,
    *,
    family_id: str,
    student_id: str,
    belong_date: str = "2026-09-10",
    status: str = "published",
) -> str:
    """直接落一行真实 tasks（事实层按天），用于满足 photos.task_id FK 的窗口任务引用。"""
    from app.modules.m001.models.orm import Task

    task_id = str(uuid4())
    with factory() as session:
        session.add(
            Task(
                task_id=task_id,
                family_id=family_id,
                student_id=student_id,
                category="school",
                belong_date=belong_date,
                week_index=1,
                window_type="day",
                spec_status="parsed",
                title="数学作业",
                status=status,
            )
        )
        session.commit()
    return task_id


def valid_jpeg(bg: int = 205) -> bytes:
    """合成一张可通过质检的作业图（JPEG）。"""
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (bg, bg, bg))
    draw = ImageDraw.Draw(img)
    y = 60
    while y < h - 60:
        draw.rectangle([60, y, w - 60, y + 12], fill=0)
        y += 60
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def dark_jpeg() -> bytes:
    """明显过暗、应触发 too_dark 的图片。"""
    img = Image.new("RGB", (320, 240), (15, 15, 15))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()
