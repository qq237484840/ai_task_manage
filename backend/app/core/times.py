"""时间工具 —— 全项目统一 UTC ISO-8601（契约：时间一律 UTC ISO-8601）。

存储格式统一 `YYYY-MM-DDTHH:MM:SS.mmmZ`（毫秒、Z 后缀），字符串同构可直接排序/比较。
"""
from datetime import datetime, timedelta, timezone

_UTC = timezone.utc


def now_iso() -> str:
    """当前 UTC 时间 ISO-8601 字符串（毫秒精度 + Z）。"""
    return datetime.now(_UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def iso_from(dt: datetime) -> str:
    return dt.astimezone(_UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def iso_plus(days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    return iso_from(datetime.now(_UTC) + timedelta(days=days, hours=hours, minutes=minutes))


def is_expired(iso_value: str | None) -> bool:
    """ISO 时间是否已过期（None 视为未过期）。"""
    if not iso_value:
        return False
    return parse_iso(iso_value) <= datetime.now(_UTC)
