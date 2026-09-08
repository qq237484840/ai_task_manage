"""SQLAlchemy 2.0 engine / session 基础设施（ADR-004：SQLite 起步，抽象为 PostgreSQL 迁移预留）。

ORM 类定义于 modules/m001/models/orm.py；本文件只负责 engine 与 session 工厂。
所有引擎访问均来自应用装配（create_app）或测试 fixture —— 不在此处持有隐式全局库连接。
"""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


def _sqlite_path(database_url: str) -> str | None:
    """sqlite:///relative|abs 形式下返回 DB 文件路径（内存库返回 None）。"""
    if not database_url.startswith("sqlite:///"):
        return None
    path = database_url.removeprefix("sqlite:///")
    if path in (":memory:", ""):
        return None
    return path


def build_engine(database_url: str) -> Engine:
    """依据 URL 构建 engine；SQLite 时确保父目录存在并开启外键约束。

    SQLite 默认不启用 FK（PRAGMA foreign_keys=OFF）；契约要求 schools/students/tasks
    引用完整（MODULE_DATA：DB FK + 应用校验双保险），因此在连接层统一开启。
    """
    is_sqlite = database_url.startswith("sqlite")
    db_path = _sqlite_path(database_url)
    if db_path:
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)
    if is_sqlite:

        def _enable_fk(dbapi_connection, _connection_record):  # pragma: no cover - 事件回调
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listen(engine, "connect", _enable_fk)
    return engine


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
