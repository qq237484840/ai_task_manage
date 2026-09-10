"""M001 测试辅助（Task-007 / 契约 v0.2.0）：新契约 payload + 固定归属窗口注入。

`conftest.py` 为 PM 独占文件（不改）；本模块以新文件形式提供新契约下的公共助手。
"""
from __future__ import annotations

from datetime import date

from app.core.config import Settings
from app.modules.m001.services.window_resolver import DefaultWindowResolver

# 固定基准日期（2026-09-10 为周四）：
TEST_TERM_START = "2026-09-01"  # 周二 → 所在周周一 = 2026-08-31
DAY = "2026-09-09"  # 周三 → day
FRIDAY = "2026-09-11"  # 周五 → weekend
MONDAY_NEXT = "2026-09-14"  # 次周周一 → day


class FixedResolver(DefaultWindowResolver):
    """测试用解析器：`resolve` 恒返回指定归属日对应窗口（隔离真实时钟）。"""

    def __init__(self, settings: Settings, belong_date: str):
        super().__init__(settings)
        self._belong_date = belong_date

    def resolve(self, ts):  # noqa: ANN001
        return self.window_for_date(date.fromisoformat(self._belong_date))


def settings_with(client, **overrides) -> Settings:
    return client.app.state.settings.model_copy(update=overrides)


def install_fixed_window(client, belong_date: str, **overrides) -> FixedResolver:
    """把固定窗口解析器注入应用（`deps.get_window_resolver` 优先读 app.state）。"""
    resolver = FixedResolver(settings_with(client, **overrides), belong_date)
    client.app.state.window_resolver = resolver
    return resolver


def text_source(text: str, seq: int = 1) -> dict:
    return {"seq": seq, "kind": "text", "text_content": text}


def image_source(photo_id: str, seq: int = 1) -> dict:
    return {"seq": seq, "kind": "image", "photo_id": str(photo_id)}


def task_payload(student_id, *, sources: list[dict] | None = None, grade_level: str | None = "三年级", **overrides) -> dict:
    payload = {
        "student_id": str(student_id),
        "category": "school",
        "grade_level": grade_level,
        "sources": [text_source("数学：练习册 P23 第 1-10 题")] if sources is None else sources,
    }
    payload.update(overrides)
    return payload


def create_task_v2(client, headers: dict, payload: dict) -> dict:
    resp = client.post("/api/v1/tasks", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
