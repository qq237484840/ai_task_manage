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
    # H5 静态目录（ADR-012：Vite 构建产物 frontend/dist，由 FastAPI 托管；
    #   dev 前端由 Vite dev server 提供；AT_FRONTEND_DIR 可覆盖）
    frontend_dir: str = str(_PROJECT_ROOT / "frontend" / "dist")

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

    # ---- 归属与窗口配置（CR-003 / ADR-013；登记见 docs/CONFIGURATION.md）----
    # 生效与锁定规则：变更只影响未聚合对象；已聚合按 task_groups.policy_version（5 条规则见 CONFIGURATION §一）
    timezone: str = "Asia/Shanghai"  # AT_TIMEZONE：归属日 / 周次计算时区（固定不跟随设备）
    term_start: str = ""  # AT_TERM_START：学期开始日 ISO 日期（week_index 起算基准 = 该日所在周的周一）
    term_end: str = ""  # AT_TERM_END：学期结束日 ISO 日期（区间外 = 假期）
    day_cutoff: str = "04:00"  # AT_DAY_CUTOFF：归属日边界，belong_date = (ts - cutoff).date()

    @property
    def day_cutoff_parts(self) -> tuple[int, int]:
        """解析 `day_cutoff`（HH:MM）为 (hour, minute)，非法值回退 04:00。"""
        try:
            hour_s, _, minute_s = self.day_cutoff.partition(":")
            hour, minute = int(hour_s), int(minute_s or 0)
        except (TypeError, ValueError):
            return 4, 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return 4, 0
        return hour, minute

    @property
    def policy_version(self) -> str:
        """当前生效的窗口/归属策略版本标识（写入 `task_groups.policy_version`）。"""
        return f"v1:{self.timezone}|{self.term_start}|{self.term_end}|{self.day_cutoff}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
