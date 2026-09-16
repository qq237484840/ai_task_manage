"""集成级（真实装配）：`photos` 窗口归属冗余（`CR-006` 子项 A / `Task-022 §3.11`）。

覆盖：

1. **上传即落归属**（**真实 M001 归属引擎**，`DefaultWindowResolver`，**无桩**）：
   - 周三 → 日窗口：`group_key == belong_date`；
   - **周五 / 周日 → 周末窗口（合并）**：`group_key == "W:<周五>"`；
   - 同时**数据面复核**（库内实读），并断言 `task_id` 仍为 `NULL`（首条确认才写的既有语义**不变**）。
2. **过滤生效**（`belong_date` / `group_key`）+ **缺省不过滤（向后兼容哨兵）**。
3. **M001 不可用不阻断上传**（`belong_date`/`group_key` 置 `NULL`，上传仍 `201`）。
4. **单一知识源**：`app/modules/m002` 生产代码**不含**归属规则本地实现（静态断言）。

**桩说明（PM 铁律 ①）**：仅用例 3 注入替身（`TaskClient.resolve_window` → `None`，验证降级路径）；
用例 1/2/4 走**真实归属引擎 + 真实上传链路**（真实质检），结论不依赖桩。

**时刻控制**：M001 归属引擎按**上传时刻**解析（`resolve_window(now)`），故用例 1/2 冻结
`upload_service` 模块内的 `datetime`（`_FrozenDateTime`）以取得可精确断言的 `belong_date`/`group_key`。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

import pytest

from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.domain.models import Photo
from app.modules.m002.services import upload_service
from tests.conftest import create_student
from tests.m002_support import valid_jpeg

WED = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)  # 周三（Asia/Shanghai 20:00）→ 日窗口
FRI = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)  # 周五 → 周末窗口
SUN = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)  # 周日 → 同一周末窗口（合并）


class _FrozenDateTime(datetime):
    """固定 `upload_service` 内 `datetime.now(tz)` —— 归属解析的采样时刻。"""

    frozen: ClassVar[datetime] = WED

    @classmethod
    def now(cls, tz=None):  # noqa: ANN001, D102
        return cls.frozen if tz is None else cls.frozen.astimezone(tz)


@pytest.fixture
def freeze_upload_now(monkeypatch):
    """把上传时刻固定为给定时刻（仅替换 `upload_service` 模块内的 `datetime` 名字）。"""

    def _apply(ts: datetime) -> None:
        _FrozenDateTime.frozen = ts
        monkeypatch.setattr(upload_service, "datetime", _FrozenDateTime)

    return _apply


def _student(world, name: str) -> dict:
    return create_student(
        world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name=name
    )


def _upload(world, student_id: str) -> dict:
    """真实上传链路（批次 → multipart 上传），返回 `POST /photos` 响应体。"""
    c, ha = world["client"], world["ha"]
    batch = c.post(
        "/api/v1/upload-batches",
        json={"student_id": student_id, "kind": "homework"},
        headers=ha,
    )
    assert batch.status_code == 201, batch.text
    resp = c.post(
        "/api/v1/photos",
        data={"batch_id": batch.json()["batch_id"]},
        files={"file": ("page.jpg", valid_jpeg(), "image/jpeg")},
        headers=ha,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------- 1) 上传即落归属
@pytest.mark.parametrize(
    ("frozen", "expect_belong", "expect_group"),
    [
        (WED, "2026-09-16", "2026-09-16"),  # 周三 → 日窗口
        (FRI, "2026-09-18", "W:2026-09-18"),  # 周五 → 周末窗口
        (SUN, "2026-09-20", "W:2026-09-18"),  # 周日 → 同一周末窗口（**合并**）
    ],
)
def test_upload_persists_window_belong_from_m001_engine(
    world, factory, freeze_upload_now, frozen, expect_belong, expect_group
):
    """真实 M001 归属引擎（**无桩**）：上传即落 `belong_date`/`group_key`（含周末合并）。"""
    stu = _student(world, f"小W{expect_group[-2:]}")
    freeze_upload_now(frozen)

    photo = _upload(world, stu["student_id"])

    assert photo["belong_date"] == expect_belong, photo
    assert photo["group_key"] == expect_group, photo

    # 数据面复核（响应不是唯一证据）
    with factory() as session:
        row = session.get(Photo, photo["photo_id"])
        assert row is not None
        assert row.belong_date == expect_belong
        assert row.group_key == expect_group
        assert row.task_id is None, "`task_id` 仍仅在首条挂接确认时写（既有语义不变）"


# ---------------------------------------------------------------- 2) 过滤 + 向后兼容
def test_list_photos_filters_by_belong_date_and_group_key(world, freeze_upload_now):
    """`belong_date`/`group_key` 过滤命中；**缺省不过滤**（向后兼容哨兵）。"""
    c, ha = world["client"], world["ha"]
    stu_a, stu_b = _student(world, "小A"), _student(world, "小B")

    freeze_upload_now(WED)
    p_wed = _upload(world, stu_a["student_id"])
    freeze_upload_now(FRI)
    p_fri = _upload(world, stu_b["student_id"])

    def items(query: str = "") -> list[dict]:
        resp = c.get(f"/api/v1/photos{query}", headers=ha)
        assert resp.status_code == 200, resp.text
        return resp.json()["items"]

    assert [i["photo_id"] for i in items("?belong_date=2026-09-16")] == [p_wed["photo_id"]]
    assert [i["photo_id"] for i in items("?belong_date=2026-09-18")] == [p_fri["photo_id"]]
    assert [i["photo_id"] for i in items("?group_key=W:2026-09-18")] == [p_fri["photo_id"]]
    assert items("?belong_date=2026-01-01") == []

    # **向后兼容哨兵**：缺省参数 → 两张都在（与改动前语义等价）
    all_items = items()
    assert {i["photo_id"] for i in all_items} == {p_wed["photo_id"], p_fri["photo_id"]}
    assert all(i["belong_date"] is not None for i in all_items), "新增字段随行返回"


# ---------------------------------------------------------------- 3) 不阻断
def test_upload_succeeds_when_m001_window_unavailable(world, factory, monkeypatch):
    """**不阻断**：M001 归属解析不可用 → 上传仍 `201`，两列置 `NULL`，列表照常可用。

    替身说明（PM 铁律 ①）：`TaskClient.resolve_window` 被替换为恒 `None`（模拟 M001 未就绪/异常），
    仅用于验证**降级路径**；本用例结论 = 「降级不阻断」，属该替身的目标语义。
    """
    c, ha = world["client"], world["ha"]
    monkeypatch.setattr(TaskClient, "resolve_window", staticmethod(lambda ts: None))
    stu = _student(world, "小D")

    photo = _upload(world, stu["student_id"])

    assert photo["belong_date"] is None and photo["group_key"] is None
    with factory() as session:
        row = session.get(Photo, photo["photo_id"])
        assert row is not None
        assert row.belong_date is None and row.group_key is None

    assert c.get("/api/v1/photos", headers=ha).status_code == 200
    assert c.get("/api/v1/photos?belong_date=2026-09-16", headers=ha).json()["total"] == 0


# ---------------------------------------------------------------- 4) 单一知识源
def test_m002_has_no_local_window_rule_implementation():
    """**单一知识源**：M002 生产代码不得复制归属规则（4 点日界 / 周末合并 / 聚合键拼装）。"""
    root = Path(__file__).resolve().parents[2] / "app" / "modules" / "m002"
    assert root.is_dir(), root
    forbidden = (
        "day_cutoff",
        "AT_DAY_CUTOFF",
        "week_index_for_date",
        'f"W:',
        '"W:{',
        'group_key = f"',
    )
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        offenders.extend(f"{path.name}:{token}" for token in forbidden if token in text)
    assert offenders == [], f"M002 出现归属规则本地实现：{offenders}"
