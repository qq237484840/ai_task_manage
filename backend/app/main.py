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

    from app.api.v1 import family, schools, students, tasks

    api_prefix = "/api/v1"
    app.include_router(family.router, prefix=api_prefix)
    app.include_router(students.router, prefix=api_prefix)
    app.include_router(tasks.router, prefix=api_prefix)
    app.include_router(schools.router, prefix=api_prefix)

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

    # ---- H5 静态托管（零构建前端；目录不存在则跳过，仅 API）----
    if mount_frontend:
        frontend_dir = Path(settings.frontend_dir).resolve()
        if frontend_dir.is_dir():
            app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
