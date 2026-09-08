"""M001 应用配置。

契约 Configuration 表（MODULE_CONTRACT.md v0.1.1）的实现登记：
- task.status_flow / subject.recommended / item_type.enum / school.stage.recommended
- pagination.default/max / auth.session_ttl / security.password_hash
配置项以 `AT_` 前缀环境变量可覆盖（如 AT_DATABASE_URL、AT_FRONTEND_DIR）。
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/app/core/config.py -> 项目根


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AT_", env_file=".env", extra="ignore")

    app_name: str = "AI Task Management (M001)"

    # 存储（ADR-004：SQLite 单文件，默认 backend/data/app.db）
    database_url: str = "sqlite:///" + (_PROJECT_ROOT / "backend" / "data" / "app.db").as_posix()
    # H5 静态目录（零构建前端，由 FastAPI 托管）
    frontend_dir: str = str(_PROJECT_ROOT / "frontend")

    # 认证（契约 Security / Configuration）
    auth_session_ttl_days: int = 30
    login_max_failures: int = 5
    login_lock_minutes: int = 5

    # 密码哈希 scrypt 参数（契约 security.password_hash = scrypt 标准库）
    scrypt_n: int = 2**14
    scrypt_r: int = 8
    scrypt_p: int = 1

    # 分页（契约 pagination.default）
    pagination_default_size: int = 20
    pagination_max_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
