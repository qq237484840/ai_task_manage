"""统一异常与错误体（契约 Failure Behavior：ErrorResponse{code,message,request_id}）。

异常层级（MODULE_DESIGN）：Validation(422) / Unauthorized(401) / PermissionDenied(403/404) /
NotFound(404) / Conflict(409) / Internal(500)。全部经 main 全局处理器转为统一 ErrorResponse。
"""
from __future__ import annotations


class AppError(Exception):
    """业务异常基类。message 面向用户可见，禁止携带密码/token/敏感内容。"""

    http_status: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status


class UnauthorizedError(AppError):
    http_status = 401
    code = "UNAUTHORIZED"


class PermissionDeniedError(AppError):
    http_status = 403
    code = "PERMISSION_DENIED"


class NotFoundError(AppError):
    http_status = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    http_status = 409
    code = "CONFLICT"


class InvalidTransitionError(ConflictError):
    code = "INVALID_TRANSITION"


class ValidationAppError(AppError):
    http_status = 422
    code = "VALIDATION_ERROR"


class BadRequestAppError(AppError):
    http_status = 400
    code = "BAD_REQUEST"


class InternalAppError(AppError):
    http_status = 500
    code = "INTERNAL_ERROR"
