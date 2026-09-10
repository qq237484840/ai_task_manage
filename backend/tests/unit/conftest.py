"""单元测试公共 fixture：AI 接入层独立 SQLite 会话（与业务库解耦）。"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, build_engine, build_session_factory


@pytest.fixture
def ai_session(tmp_path) -> Session:
    """每用例独立 SQLite 临时库的 Session（用于 DATA-009 调用记录断言）。"""
    engine = build_engine("sqlite:///" + (tmp_path / "ai.db").as_posix())
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
