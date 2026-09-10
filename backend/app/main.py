"""应用装配：FastAPI 单体（ADR-004）。

职责：路由挂载（/api/v1）、异常统一错误体（ErrorResponse + request_id 贯穿）、
CORS、H5 静态托管、启动时建表 + schools seed（幂等）。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, get_settings
from app.core.database import Base, build_engine, build_session_factory
from app.core.logging import RequestIdMiddleware, get_request_id, setup_logging
from app.core.seed import seed_schools
from app.modules.m001.schemas.common import ErrorResponse
from app.shared.exceptions import AppError


def _error_body(code: str, message: str) -> dict:
    return ErrorResponse(code=code, message=message, request_id=get_request_id()).model_dump()


def create_app(settings: Settings | None = None, *, mount_frontend: bool = True) -> FastAPI:
    setup_logging()
    settings = settings or get_settings()
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(bind=engine)
        with session_factory() as session:
            seed_schools(session)
            session.commit()
        yield

    app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.v1 import family, schools, student_auth, students, task_groups, tasks
    # M002（Task-002/Task-008）：作业图片采集与归属 —— 独立模块路由
    #   （含 upload-batches/photos/挂接复核 /**link-suggestions + photo-gates**/**completion-analyses**）
    from app.modules.m002.api import (
        analysis_routes,
        association_routes,
        link_routes,
        photo_routes,
        upload_routes,
    )
    # 跨模块回调注册的唯一通道（M001 不反向 import M002）：M002 导入期已自动注册一次，
    #   此处启动期再幂等调用一次自愈（覆盖「首次导入时 M001 聚合层尚未就绪」的场景）
    from app.modules.m002.clients.task_client import ensure_links_migration_hook_registered

    api_prefix = "/api/v1"
    app.include_router(family.router, prefix=api_prefix)
    app.include_router(student_auth.router, prefix=api_prefix)
    app.include_router(students.router, prefix=api_prefix)
    app.include_router(tasks.router, prefix=api_prefix)
    app.include_router(task_groups.router, prefix=api_prefix)
    app.include_router(schools.router, prefix=api_prefix)
    app.include_router(upload_routes.router, prefix=api_prefix)
    app.include_router(photo_routes.router, prefix=api_prefix)
    app.include_router(association_routes.router, prefix=api_prefix)
    app.include_router(link_routes.router, prefix=api_prefix)
    app.include_router(analysis_routes.router, prefix=api_prefix)

    # M001→M002 挂接迁移回调：启动期幂等自愈（「导入期 + 启动期」双保险；
    #   未就绪时仅 warning，不阻断装配）
    ensure_links_migration_hook_registered()

    # ---- 统一错误体（契约 Failure Behavior）----
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        try:
            first = exc.errors()[0]
            detail = first.get("msg", "")
        except (IndexError, KeyError, TypeError):
            detail = ""
        return JSONResponse(
            status_code=422,
            content=_error_body("VALIDATION_ERROR", f"请求参数校验失败{f': {detail}' if detail else ''}"),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("uvicorn.error").exception("unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content=_error_body("INTERNAL_ERROR", "服务器内部错误"))

    # ---- H5 静态托管（ADR-012：Vite 构建产物 frontend/dist 由 FastAPI 托管；
    #       dev 时前端由 Vite dev server（/api/v1 代理）提供；目录不存在则跳过，仅 API）----
    if mount_frontend:
        frontend_dir = Path(settings.frontend_dir).resolve()
        if frontend_dir.is_dir():
            app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
