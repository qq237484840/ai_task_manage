"""M001 内部接口桥（聚合层，契约 M001 v0.2.0 Frozen；M002 v0.4.0 消费面）。

边界规则（MODULE_CONTRACT 依赖/架构约束）：
- M002 不直读/不改 M001 业务表；一切跨模块调用经本客户端（唯一收敛点）。
- M001 内部"不存在/越权"抛 PermissionDeniedError（403 语义），此处统一转 NotFoundError
  （对外 404 防探测），并在 docstring 注明转换点。
- 聚合层接口（list_groups / get_group / ensure_group / commit_conclusion）由 m001-dev（Task-007）
  并行实现；本模块采用**延迟导入 + 可注入 port**：
- `get_group_subject` **不是** M001 契约接口（M001 v0.2.0 内部服务接口表未登记，属 M001 内部实现
  细节），其 `TaskGroupSubjectDTO` 不含 group 上下文；M002 侧统一经契约内 `list_groups` 定位并
  回填 group 上下文（BUG-002 修复），不再消费 M001 内部实现细节。
  * 默认实现（DefaultM001Gateway）在运行时可用时按契约签名调用；
  * 运行时尚不可用 → 抛 M001UnavailableError（503），由调用方降级/上报；
  * 测试可注入契约桩（set_gateway），不复制 M001 业务逻辑。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.modules.m002.domain.errors import (
    LinkTargetMissingError,
    M001UnavailableError,
    NotFoundError,
)
from app.shared.exceptions import PermissionDeniedError

logger = logging.getLogger("m002.task_client")


@dataclass(frozen=True)
class GroupSubjectRef:
    """M002 侧消费视图：聚合学科子任务（归属目标 = task_group_subjects）。

    window_task_id / task_status 为 M001 聚合层回传的窗口级冗余信息（用于 photos.task_id
    与首确认 mark_in_progress）；M001 契约若未暴露，则为 None（不阻断挂接，仅跳过窗口任务联动）。
    """

    group_subject_id: str
    subject: str
    student_id: str
    group_id: str
    group_key: str
    window_type: str
    category: str | None = None
    window_task_id: str | None = None
    task_status: str | None = None
    conclusion: str | None = None
    conclusion_status: str | None = None


@dataclass(frozen=True)
class TaskGroupRef:
    """M002 侧消费视图：聚合对象（task_groups）+ 学科子任务集合。"""

    group_id: str
    student_id: str
    category: str
    group_key: str
    window_type: str
    display_name: str | None = None
    policy_version: str | None = None
    window_task_id: str | None = None
    task_status: str | None = None
    subjects: list[GroupSubjectRef] = field(default_factory=list)


class M001Gateway(Protocol):
    """M002 → M001 聚合层消费契约（签名对齐 docs/modules/M001/MODULE_API.md）。"""

    def student_exists(self, session: Session, family_id: str, student_id: str) -> bool: ...

    def get_task(self, session: Session, family_id: str, task_id: str) -> Any: ...

    def mark_in_progress(self, session: Session, family_id: str, task_id: str) -> tuple[str, str]: ...

    def list_groups(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        group_key: str | None = None,
    ) -> list[TaskGroupRef]: ...

    def get_group(self, session: Session, family_id: str, group_id: str) -> TaskGroupRef: ...

    def ensure_group(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str,
        category: str,
        belong_date: str,
    ) -> TaskGroupRef: ...

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
    ) -> Any: ...

    def get_group_subject(
        self, session: Session, family_id: str, group_subject_id: str
    ) -> GroupSubjectRef: ...


def _attr(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _to_subject_ref(raw: Any, group: Any) -> GroupSubjectRef:
    return GroupSubjectRef(
        group_subject_id=str(_attr(raw, "group_subject_id", "id", "subject_id")),
        subject=str(_attr(raw, "subject", "subject_name") or ""),
        student_id=str(_attr(raw, "student_id") or _attr(group, "student_id") or ""),
        group_id=str(_attr(raw, "group_id") or _attr(group, "group_id") or ""),
        group_key=str(_attr(raw, "group_key") or _attr(group, "group_key") or ""),
        window_type=str(_attr(raw, "window_type") or _attr(group, "window_type") or ""),
        category=_attr(raw, "category") or _attr(group, "category"),
        window_task_id=_attr(raw, "window_task_id", "task_id") or _attr(group, "window_task_id", "task_id"),
        task_status=_attr(raw, "task_status") or _attr(group, "task_status"),
        conclusion=_attr(raw, "conclusion"),
        conclusion_status=_attr(raw, "conclusion_status", "status"),
    )


def _to_group_ref(raw: Any) -> TaskGroupRef:
    raw_subjects = _attr(raw, "subjects", "group_subjects", "items") or []
    subjects = [_to_subject_ref(s, raw) for s in raw_subjects]
    return TaskGroupRef(
        group_id=str(_attr(raw, "group_id", "id")),
        student_id=str(_attr(raw, "student_id") or ""),
        category=str(_attr(raw, "category") or ""),
        group_key=str(_attr(raw, "group_key") or ""),
        window_type=str(_attr(raw, "window_type") or ""),
        display_name=_attr(raw, "display_name"),
        policy_version=_attr(raw, "policy_version"),
        window_task_id=_attr(raw, "window_task_id", "task_id"),
        task_status=_attr(raw, "task_status"),
        subjects=subjects,
    )


class DefaultM001Gateway:
    """默认网关：延迟导入 M001 服务，运行时就绪则按契约调用，否则抛 M001UnavailableError。"""

    # —— 既有（Task-002 冻结段，M001 已实现）——
    def student_exists(self, session: Session, family_id: str, student_id: str) -> bool:
        from app.modules.m001.services.family_space import FamilySpaceService

        try:
            FamilySpaceService.get_student(session, family_id, student_id)
            return True
        except PermissionDeniedError:
            return False

    def get_task(self, session: Session, family_id: str, task_id: str) -> Any:
        from app.modules.m001.services.task_service import TaskQueryService

        try:
            return TaskQueryService.get_task(session, family_id, task_id)
        except PermissionDeniedError as exc:
            raise NotFoundError(exc.message) from exc

    def mark_in_progress(self, session: Session, family_id: str, task_id: str) -> tuple[str, str]:
        from app.modules.m001.services.task_state import TaskStateService

        return TaskStateService.mark_in_progress(session, family_id, task_id)

    # —— 聚合层（Task-007 并行实现；未就绪 → M001UnavailableError）——
    @staticmethod
    def _group_service() -> Any:
        try:
            from app.modules.m001.services import task_group_service as mod
        except ImportError as exc:  # pragma: no cover - 运行时就绪后不再触发
            raise M001UnavailableError(
                "M001 聚合层（task_group_service）尚未就绪，请注入契约桩或稍后联调"
            ) from exc
        service = getattr(mod, "TaskGroupService", None)
        if service is None:  # pragma: no cover
            raise M001UnavailableError("M001 TaskGroupService 缺失，需联调")
        return service

    def list_groups(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        group_key: str | None = None,
    ) -> list[TaskGroupRef]:
        service = self._group_service()
        method = getattr(service, "list_groups", None)
        if method is None:  # pragma: no cover
            raise M001UnavailableError("M001 TaskGroupService.list_groups 缺失，需联调")
        # TD-003（Task-014 清理）：按 M001 v0.2.0 Frozen 契约直调，**不得**再以
        # `except TypeError` 静默容忍签名漂移（BUG-004 教训：兼容垫片会掩盖契约缺口）。
        rows = method(session, family_id, student_id=student_id, group_key=group_key)
        return [_to_group_ref(r) for r in rows]

    def get_group(self, session: Session, family_id: str, group_id: str) -> TaskGroupRef:
        service = self._group_service()
        method = getattr(service, "get_group", None)
        if method is None:  # pragma: no cover
            raise M001UnavailableError("M001 TaskGroupService.get_group 缺失，需联调")
        try:
            raw = method(session, family_id, group_id)
        except PermissionDeniedError as exc:
            raise LinkTargetMissingError("聚合对象不存在或无权访问") from exc
        if raw is None:
            raise LinkTargetMissingError("聚合对象不存在")
        return _to_group_ref(raw)

    def ensure_group(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str,
        category: str,
        belong_date: str,
    ) -> TaskGroupRef:
        service = self._group_service()
        method = getattr(service, "ensure_group", None)
        if method is None:  # pragma: no cover
            raise M001UnavailableError("M001 TaskGroupService.ensure_group 缺失，需联调")
        raw = method(
            session, family_id, student_id=student_id, category=category, belong_date=belong_date
        )
        return _to_group_ref(raw)

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
        service = self._group_service()
        method = getattr(service, "commit_conclusion", None)
        if method is None:  # pragma: no cover
            raise M001UnavailableError("M001 TaskGroupService.commit_conclusion 缺失，需联调")
        return method(
            session,
            family_id,
            group_subject_id=group_subject_id,
            conclusion=conclusion,
            evidence_photo_ids=evidence_photo_ids,
            confidence=confidence,
            status=status,
        )

    def get_group_subject(
        self, session: Session, family_id: str, group_subject_id: str
    ) -> GroupSubjectRef:
        """定位聚合学科子任务（M002 消费视图）。

        默认路径 = **M001 契约内接口**（MODULE_API 内部服务接口表：`list_groups` / `get_group`）：
        经 `list_groups(session, family_id)` 扫描 `TaskGroupDTO.subjects` 命中即返回——group 上下文
        （`group_key` / `window_type` / `student_id` / `group_id` / `category`）由 `TaskGroupDTO` 回填。

        修复说明（BUG-002）：M001 `TaskGroupService.get_group_subject` **未登记**于契约内部服务接口
        表，且其 `TaskGroupSubjectDTO` 不含 group 上下文；M002 曾将其作为唯一来源 → `_to_subject_ref`
        得空 `group_key` → 门控单桶聚合、`409 gate_not_satisfied` 不可达。故此处不再采信其返回值作为
        定位结果（同为 `_to_group_ref` 全量扫描，`list_group_subjects` 亦复用该契约路径）。
        后续若 M001 将该接口登记进契约并补齐 group 字段，可恢复为「加速路径 + 失败回落契约路径」。

        异常语义不变：不存在/越权 → `LinkTargetMissingError`（对外 404 防探测）；
        M001 聚合层未就绪 → `M001UnavailableError`（503，由 `list_groups` 抛出）。
        """
        target = str(group_subject_id)
        for group in self.list_groups(session, family_id):
            for subject in group.subjects:
                if subject.group_subject_id == target:
                    return subject
        raise LinkTargetMissingError("聚合学科子任务不存在或无权访问")


_gateway: M001Gateway = DefaultM001Gateway()


def get_gateway() -> M001Gateway:
    return _gateway


def set_gateway(gateway: M001Gateway | None) -> None:
    """测试/联调注入契约桩；传 None 恢复默认。"""
    global _gateway
    _gateway = gateway or DefaultM001Gateway()


class TaskClient:
    """M002 服务层唯一跨模块调用入口（薄封装，转发到当前网关）。"""

    @staticmethod
    def student_exists(session: Session, family_id: str, student_id: str) -> bool:
        return get_gateway().student_exists(session, family_id, student_id)

    @staticmethod
    def get_task_or_404(session: Session, family_id: str, task_id: str) -> Any:
        return get_gateway().get_task(session, family_id, task_id)

    @staticmethod
    def mark_in_progress(session: Session, family_id: str, task_id: str) -> tuple[str, str]:
        return get_gateway().mark_in_progress(session, family_id, task_id)

    @staticmethod
    def list_groups(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        group_key: str | None = None,
    ) -> list[TaskGroupRef]:
        return get_gateway().list_groups(
            session, family_id, student_id=student_id, group_key=group_key
        )

    @staticmethod
    def list_group_subjects(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        group_key: str | None = None,
    ) -> list[GroupSubjectRef]:
        groups = get_gateway().list_groups(
            session, family_id, student_id=student_id, group_key=group_key
        )
        return [subject for group in groups for subject in group.subjects]

    @staticmethod
    def get_group(session: Session, family_id: str, group_id: str) -> TaskGroupRef:
        return get_gateway().get_group(session, family_id, group_id)

    @staticmethod
    def ensure_group(
        session: Session,
        family_id: str,
        *,
        student_id: str,
        category: str,
        belong_date: str,
    ) -> TaskGroupRef:
        return get_gateway().ensure_group(
            session, family_id, student_id=student_id, category=category, belong_date=belong_date
        )

    @staticmethod
    def get_group_subject(
        session: Session, family_id: str, group_subject_id: str
    ) -> GroupSubjectRef:
        return get_gateway().get_group_subject(session, family_id, group_subject_id)

    @staticmethod
    def commit_conclusion(
        session: Session,
        family_id: str,
        *,
        group_subject_id: str,
        conclusion: str,
        evidence_photo_ids: list[str],
        confidence: float | None,
        status: str,
    ) -> Any:
        return get_gateway().commit_conclusion(
            session,
            family_id,
            group_subject_id=group_subject_id,
            conclusion=conclusion,
            evidence_photo_ids=evidence_photo_ids,
            confidence=confidence,
            status=status,
        )


def migrate_photo_links(
    session: Session,
    family_id: str,
    task_id: str,
    old_group_key: str,
    new_group_key: str,
) -> None:
    """M001 → M002 挂接迁移钩子（M001 `migrate_links_hook` 以关键字回调；M001 不 import M002）。

    由 M001 在改归属日跨聚合时调用；失败上抛令整体事务回滚（保持一致性）。
    """
    from app.modules.m002.services.link_service import LinkService

    task = TaskClient.get_task_or_404(session, family_id, task_id)
    student_id = str(getattr(task, "student_id", "") or "")
    if not student_id:
        return
    LinkService.migrate_links(
        session,
        family_id,
        student_id=student_id,
        old_group_key=old_group_key,
        new_group_key=new_group_key,
    )


def ensure_links_migration_hook_registered() -> bool:
    """幂等注册 M001→M002 挂接迁移回调（公开入口）。

    由 M002 模块导入期自动调用一次；`create_app()` 启动期可**再次**调用以幂等自愈
    （例如首次导入时 M001 聚合层尚未就绪）。

    返回语义：
    - M001 槽位已是本函数 → True（短路，不重复写）；
    - 本次注册成功 → True；
    - M001 聚合层不可用（ImportError）或注册抛错 → False（记 warning，不抛、不阻断）。
    """
    try:
        from app.modules.m001.services import aggregation_service as _ag
        from app.modules.m001.services.aggregation_service import (
            register_links_migration_hook,
        )
    except ImportError:  # M001 聚合层未就绪（唯一预期情形）
        logger.warning("M001 聚合层未就绪，挂接迁移回调注册跳过", exc_info=True)
        return False

    if getattr(_ag, "_links_migration_hook", None) is migrate_photo_links:
        return True  # 已注册（幂等短路，不重复写）

    try:
        register_links_migration_hook(migrate_photo_links)
    except Exception:  # noqa: BLE001 - 注册失败不阻断导入/启动
        logger.warning("注册 M001 挂接迁移回调失败", exc_info=True)
        return False
    return True


def _register_links_migration_hook() -> None:
    """模块导入期自动注册一次（薄封装；保持既有「导入即注册」行为）。"""
    ensure_links_migration_hook_registered()


_register_links_migration_hook()
