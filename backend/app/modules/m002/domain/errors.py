"""M002 领域错误（契约 v0.4.0 Failure Behavior 的错误码集合）。

基于 shared.exceptions.AppError 按错误码二次封装，路由/服务统一抛这类异常，
由 main 全局处理器转 ErrorResponse{code,message,request_id}。
"""
from __future__ import annotations

from app.shared.exceptions import (
    AppError,
    ConflictError,
    InternalAppError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)


class UnsupportedMediaError(AppError):
    """415 unsupported_media_type。"""

    http_status = 415
    code = "unsupported_media_type"


class ImageTooLargeError(AppError):
    """413 image_too_large（单图 > 10MB）。"""

    http_status = 413
    code = "image_too_large"


class ImageQualityRejectedError(ValidationAppError):
    """422 image_quality_rejected（不合格不入库；message 含逐项原因）。"""

    code = "image_quality_rejected"


class BatchPhotoLimitError(ValidationAppError):
    """422 batch_photo_limit（批次达上限）。"""

    code = "batch_photo_limit"


class PixelLimitError(ValidationAppError):
    """422 image_pixel_limit（解码像素超限）。"""

    code = "image_pixel_limit"


class TaskPhotoLimitError(ConflictError):
    """409 task_photo_limit（窗口任务 assigned 达上限）。"""

    code = "task_photo_limit"


class SubjectPhotoLimitError(ConflictError):
    """409 subject_photo_limit（单个聚合学科子任务挂接照片达上限）。"""

    code = "subject_photo_limit"


class TaskNotAcceptableError(ConflictError):
    """409 task_not_acceptable（窗口任务状态不允许归属；附当前状态）。"""

    code = "task_not_acceptable"

    def __init__(self, status: str, message: str | None = None):
        super().__init__(message or f"任务状态 {status} 不允许归属（需已发布或进行中）")
        self.task_status = status


class PhotoConsumedError(ConflictError):
    """409 photo_consumed（已消费照片不可删/不可改派）。"""

    code = "photo_consumed"


class ConcurrentConflictError(ConflictError):
    """409 concurrent_conflict（同批次上传/归属并发争用）。"""

    code = "concurrent_conflict"


class GateNotSatisfiedError(ConflictError):
    """409 gate_not_satisfied（窗口仍有未确认挂接照片，禁止生成/重跑分析）。"""

    code = "gate_not_satisfied"

    def __init__(self, pending: int, message: str | None = None):
        super().__init__(message or f"待复核 {pending} 张")
        self.pending = pending


class LinkStateError(ConflictError):
    """409 link_state（挂接复核动作与当前状态不匹配，如 reject 已确认 link）。"""

    code = "link_state"


class AnalysisStateError(ConflictError):
    """409 analysis_state（分析状态不允许该操作，如重跑已确认分析）。"""

    code = "analysis_state"


class AnalysisConfirmedError(ConflictError):
    """409 analysis_confirmed（已确认分析不可再确认/覆盖）。"""

    code = "analysis_confirmed"


class InvalidConclusionError(ValidationAppError):
    """422 invalid_conclusion（结论不在枚举内）。"""

    code = "invalid_conclusion"


class LinkTargetMissingError(NotFoundError):
    """404 link_target_missing（挂接目标聚合学科子任务不存在或不属于该学生）。"""

    code = "link_target_missing"


class LinkMissingError(ValidationAppError):
    """422 link_missing（复核动作缺少 link_id / group_subject_id）。"""

    code = "link_missing"


class KindMismatchError(ValidationAppError):
    """422 kind_mismatch（入口 kind 与操作不匹配）。"""

    code = "kind_mismatch"


class M001UnavailableError(InternalAppError):
    """503 m001_unavailable（M001 聚合层内部接口暂不可用，需联调）。"""

    http_status = 503
    code = "m001_unavailable"


class AiUnavailableError(InternalAppError):
    """503 ai_unavailable（AI 接入层不可用；调用方须降级，不得产生脏数据）。"""

    http_status = 503
    code = "ai_unavailable"


__all__ = [
    "AppError",
    "UnauthorizedError",
    "NotFoundError",
    "ConflictError",
    "InternalAppError",
    "ValidationAppError",
    "UnsupportedMediaError",
    "ImageTooLargeError",
    "ImageQualityRejectedError",
    "BatchPhotoLimitError",
    "PixelLimitError",
    "TaskPhotoLimitError",
    "SubjectPhotoLimitError",
    "TaskNotAcceptableError",
    "PhotoConsumedError",
    "ConcurrentConflictError",
    "GateNotSatisfiedError",
    "LinkStateError",
    "AnalysisStateError",
    "AnalysisConfirmedError",
    "InvalidConclusionError",
    "LinkTargetMissingError",
    "LinkMissingError",
    "KindMismatchError",
    "M001UnavailableError",
    "AiUnavailableError",
]
