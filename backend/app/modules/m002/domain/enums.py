"""M002 领域枚举（契约 v0.4.0）。

- 入口 `kind`（BatchKind）：由菜单决定（「任务」→ task_spec，「作业」→ homework）。
- 挂接来源（LinkSource）：ai | manual。
- 复核动作（LinkAction）：accept | reject | relink。
- 分析状态（AnalysisStatus）：draft | confirmed。
- 结论（Conclusion）：完成 | 部分完成 | 未完成 | 无法判断。
- 照片状态（PhotoStatus）：由挂接派生（先采后认）。
"""
from __future__ import annotations


class BatchKind:
    """上传入口 `kind`（DATA-003 修订；由菜单入口决定，后端冗余存储）。"""

    TASK_SPEC = "task_spec"  # 「任务」入口：任务说明（文字/图片/聊天记录）
    HOMEWORK = "homework"  # 「作业」入口：作业图片（不填内容）

    ALL = (TASK_SPEC, HOMEWORK)
    DEFAULT = HOMEWORK


class PhotoStatus:
    """photos.status 状态机值（由 photo_subject_links 派生，PD-015/R2）。

    unassigned →(AI suggestion)→ suggested →(accept/confirm)→ assigned
    suggested|unassigned →(全部 reject)→ rejected
    consumed_at 置位后不可再改派/删除。
    """

    UNASSIGNED = "unassigned"
    SUGGESTED = "suggested"
    ASSIGNED = "assigned"
    REJECTED = "rejected"

    ALL = (UNASSIGNED, SUGGESTED, ASSIGNED, REJECTED)


class LinkSource:
    """photo_subject_links.source。"""

    AI = "ai"
    MANUAL = "manual"

    ALL = (AI, MANUAL)


class LinkAction:
    """API-M002-005 /links 复核动作。"""

    ACCEPT = "accept"
    REJECT = "reject"
    RELINK = "relink"

    ALL = (ACCEPT, REJECT, RELINK)


class AnalysisStatus:
    """completion_analyses.status。"""

    DRAFT = "draft"
    CONFIRMED = "confirmed"

    ALL = (DRAFT, CONFIRMED)


class Conclusion:
    """completion_analyses.conclusion（聚合子任务(学科)级，不维护参考答案基准）。"""

    COMPLETED = "完成"
    PARTIAL = "部分完成"
    INCOMPLETE = "未完成"
    UNKNOWN = "无法判断"

    ALL = (COMPLETED, PARTIAL, INCOMPLETE, UNKNOWN)
    DEFAULT = UNKNOWN


class SubjectType:
    FAMILY = "family"
    STUDENT = "student"
