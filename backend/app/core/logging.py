"""日志与 request_id 贯穿（契约 Failure Behavior / 审计要求）。

- 每个请求生成 request_id（可经 X-Request-ID 传入），随响应头返回并贯穿日志（correlation）。
- `audit` logger 承载审计事件（登录/登出/任务创建/状态迁移等）。
- What Not to Log（DEVELOPMENT_GUIDE §7）：明文密码、会话 token、学生姓名、参考答案等。
"""
import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


class RequestIdFilter(logging.Filter):
    """把当前请求的 request_id 注入每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # audit 独立 logger，至少 INFO
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(handler)


def get_request_id() -> str:
    return request_id_var.get()


def audit_event(
    event: str,
    *,
    family_id: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    student_id: str | None = None,
    detail: str | None = None,
) -> None:
    """记录审计事件。敏感内容（密码/token/姓名/参考答案）禁止经 detail 传入。"""
    logger = logging.getLogger("audit")
    logger.info(
        "audit event=%s family=%s session=%s task=%s student=%s %s",
        event,
        family_id or "-",
        session_id or "-",
        task_id or "-",
        student_id or "-",
        detail or "",
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response
