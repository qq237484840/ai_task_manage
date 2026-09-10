"""归属引擎 `WindowResolver`（A5；MODULE_DESIGN.md §归属引擎 / MODULE_CONTRACT.md §F2）。

策略接口：`resolve(ts) -> WindowInfo{belong_date, week_index, window_type, group_key}`。

V1 实现 `DefaultWindowResolver`（读 `AT_TIMEZONE`/`AT_TERM_START`/`AT_TERM_END`/`AT_DAY_CUTOFF`）：
- `belong_date = (ts.astimezone(AT_TIMEZONE) - AT_DAY_CUTOFF).date()`（时间戳按 UTC 存储，仅此处转换）
- `week_index` = `AT_TERM_START` **所在周的周一**起算第 N 周
- `window_type`：周一~周四 `day`；**周五 04:00 ~ 周一 04:00** `weekend`；`AT_TERM_END` 之后 `holiday`
- `group_key`：`day`→`belong_date`；`weekend`→`W:<该周末周五 belong_date>`；`holiday`→`H:<周起始周一>.W<n>`

保底（诚实声明）：
- `AT_TERM_START` 未配置时 `week_index` 恒为 1（不阻断写入；部署侧应填写）
- 假期解析器 V1 只实现"按自然周聚合"；"整段假期 = 1 窗口"的假期计划属 V2（本任务不实现）
- 时区名非法时回退 `Asia/Shanghai`
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Protocol
from zoneinfo import ZoneInfo

from app.core.config import Settings, get_settings
from app.modules.m001.schemas.task_group import WindowInfo

_WEEKDAY_CN = "一二三四五六日"
# 无 tzdata 环境下的固定偏移回退（V1 部署时区 = Asia/Shanghai，全年 UTC+8 无夏令时）
_FIXED_OFFSET_HOURS: dict[str, int] = {"Asia/Shanghai": 8, "UTC": 0, "Etc/UTC": 0}


def parse_iso_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def day_title(belong_date: str) -> str:
    """归属日展示标题（如「09-09 周三」）。"""
    d = date.fromisoformat(belong_date)
    return f"{d.strftime('%m-%d')} 周{_WEEKDAY_CN[d.weekday()]}"


class WindowResolver(Protocol):
    """归属引擎策略接口（可替换规则）。"""

    def resolve(self, ts: datetime) -> WindowInfo: ...


class DefaultWindowResolver:
    """V1 归属引擎实现（读 4 个 `AT_*` 配置；纯计算，不写库、不锁配置）。"""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    # —— 配置读取 ——
    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def policy_version(self) -> str:
        """当前生效的窗口/归属策略版本标识（写入 `task_groups.policy_version`）。"""
        return self._settings.policy_version

    def _tz(self) -> tzinfo:
        try:
            return ZoneInfo(self._settings.timezone)
        except Exception:  # 无 tzdata / 非法时区名 → 固定偏移回退（不阻断业务）
            hours = _FIXED_OFFSET_HOURS.get(self._settings.timezone, 8)
            return timezone(timedelta(hours=hours))

    # —— 核心解析 ——
    def resolve(self, ts: datetime) -> WindowInfo:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        local = ts.astimezone(self._tz())
        hour, minute = self._settings.day_cutoff_parts
        belong = (local - timedelta(hours=hour, minutes=minute)).date()
        return self.window_for_date(belong)

    def window_for_date(self, belong: date) -> WindowInfo:
        """由归属日反解窗口（供 `ensure_group` 与改归属日使用；与 `resolve` 同源规则）。"""
        term_end = parse_iso_date(self._settings.term_end)
        if term_end is not None and belong > term_end:
            window_type = "holiday"
            monday = belong - timedelta(days=belong.weekday())
            term_end_monday = term_end - timedelta(days=term_end.weekday())
            holiday_week = max(1, (monday - term_end_monday).days // 7 + 1)
            group_key = f"H:{monday.isoformat()}.W{holiday_week}"
        elif belong.weekday() >= 4:  # 周五(4)/周六(5)/周日(6)
            window_type = "weekend"
            friday = belong - timedelta(days=belong.weekday() - 4)
            group_key = f"W:{friday.isoformat()}"
        else:  # 周一~周四
            window_type = "day"
            group_key = belong.isoformat()
        return WindowInfo(
            belong_date=belong.isoformat(),
            week_index=self.week_index_for_date(belong),
            window_type=window_type,  # type: ignore[arg-type]
            group_key=group_key,
        )

    def week_index_for_date(self, belong: date) -> int:
        """周次 = `AT_TERM_START` 所在周的周一起算第 N 周（未配置时保底 1）。"""
        term_start = parse_iso_date(self._settings.term_start)
        if term_start is None:
            return 1
        term_monday = term_start - timedelta(days=term_start.weekday())
        return max(1, (belong - term_monday).days // 7 + 1)

    @staticmethod
    def member_dates(window: WindowInfo) -> list[str]:
        """窗口成员归属日（聚合范围）：day=1 天；weekend=周五/六/日；holiday=自然周周一~周日。"""
        if window.window_type == "weekend":
            friday = date.fromisoformat(window.group_key.removeprefix("W:"))
            return [(friday + timedelta(days=i)).isoformat() for i in range(3)]
        if window.window_type == "holiday":
            monday = date.fromisoformat(window.group_key.split(":")[1].split(".")[0])
            return [(monday + timedelta(days=i)).isoformat() for i in range(7)]
        return [window.belong_date]


def group_display_name(window: WindowInfo) -> str:
    """聚合展示名：「周末作业」/「第 N 周」/ 日期（如「09-09 周三」）。"""
    if window.window_type == "weekend":
        return "周末作业"
    if window.window_type == "holiday":
        return f"第 {window.week_index} 周"
    return day_title(window.belong_date)


def get_default_resolver() -> DefaultWindowResolver:
    """默认解析器（读全局 `get_settings()`；REST 层优先用 `app.state.settings` 构建）。"""
    return DefaultWindowResolver(get_settings())
