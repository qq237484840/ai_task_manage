"""单测：M002 受控提供布置单图片（`CR-005` / `Task-018`）。

覆盖：
- `provide_task_source_image`：正常返回受控 `abs_path` / **跨家庭 → `None`** / 未知照片 → `None` / 文件缺失 → `None`；
- `ensure_task_spec_image_provider_registered`：幂等短路 / 槽位清空后**自愈** / M001 侧不可用 → `False` 且不抛。

**桩说明（PM 铁律 ①）**：仅「注册契约」两个用例以 `sys.modules` 注入**假的 M001 `image_provider` 模块**
（为验证回调注册契约；其中无业务逻辑）。**归属校验与路径解析全部走真实 `PhotoRepository` + `ImageStore`**，
无业务桩；结论不依赖桩。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.modules.m002.clients.task_client import (
    ensure_task_spec_image_provider_registered,
    provide_task_source_image,
)
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.services.image_store import ImageStore
from tests.conftest import create_student

PHOTO_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def image_root(tmp_path, monkeypatch):
    """把 M002 图片根目录指向临时目录（并清缓存，避免跨用例泄漏）。"""
    from app.modules.m002.config import get_m002_settings

    root = tmp_path / "images"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AT_M002_IMAGE_STORE_ROOT", str(root))
    get_m002_settings.cache_clear()
    yield root
    get_m002_settings.cache_clear()


def _seed_photo(world, factory, image_root: Path) -> str:
    """写入 1 行真实照片 + 真实归一图文件（`kind=task_spec`），返回相对路径。

    批次经**真实 API** 创建（满足 `photos.batch_id` 外键约束），照片行走真实仓储。
    """
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小T")
    batch_resp = c.post(
        "/api/v1/upload-batches",
        json={"student_id": stu["student_id"], "kind": "task_spec"},
        headers=ha,
    )
    assert batch_resp.status_code == 201, batch_resp.text
    batch_id = batch_resp.json()["batch_id"]
    fam = world["family_id_a"]
    store = ImageStore(image_root)
    rel = store.save_normalized(
        store.batch_rel_dir(fam, batch_id), seq_no=1, photo_id=PHOTO_ID, data=b"\xff\xd8\xff\xd9"
    )
    with factory() as s:
        PhotoRepository.create(
            s,
            photo_id=PHOTO_ID,
            batch_id=batch_id,
            family_id=fam,
            student_id=stu["student_id"],
            seq_no=1,
            kind="task_spec",
            created_by_type="family",
            created_by_id=fam,
            original_mime="image/jpeg",
            original_path=rel,
            normalized_path=rel,
            file_size_bytes=4,
            width=1,
            height=1,
            sha256="0" * 64,
            quality_report_json="{}",
        )
        s.commit()
    return rel


def test_provide_returns_controlled_abs_path(world, factory, image_root):
    """正常：本家照片 → `mime` + 存在的受控绝对路径（位于受控根目录内）。"""
    _seed_photo(world, factory, image_root)

    with factory() as s:
        ref = provide_task_source_image(s, world["family_id_a"], PHOTO_ID)

    assert ref is not None
    assert ref.mime == "image/jpeg"
    abs_path = Path(ref.abs_path)
    assert abs_path.exists(), ref.abs_path
    assert abs_path.is_relative_to(image_root.resolve())


def test_provide_rejects_cross_family(world, factory, image_root):
    """归属校验：以**另一家庭** `family_id` 查询 → `None`（不得越权取图）。"""
    _seed_photo(world, factory, image_root)

    with factory() as s:
        assert provide_task_source_image(s, world["family_id_b"], PHOTO_ID) is None


def test_provide_unknown_photo_returns_none(world, factory, image_root):
    with factory() as s:
        assert (
            provide_task_source_image(
                s, world["family_id_a"], "deadbeef-0000-0000-0000-000000000000"
            )
            is None
        )


def test_provide_missing_file_returns_none(world, factory, image_root):
    """行在、盘上文件被删 → `None`（不抛，交 M001 按「不转发」降级）。"""
    rel = _seed_photo(world, factory, image_root)
    (image_root / rel).unlink()

    with factory() as s:
        assert provide_task_source_image(s, world["family_id_a"], PHOTO_ID) is None


# ---------------------------------------------------------------- 注册契约（真实 M001 槽）
def test_register_is_idempotent_and_self_healing():
    """注册：首次成功 → 幂等短路 → 槽位清空后**可自愈**（用**真实** M001 槽位断言，无桩）。"""
    from app.modules.m001.services import image_provider as m001_ip

    original = m001_ip._task_spec_image_provider  # noqa: SLF001 - 契约槽位断言
    try:
        assert ensure_task_spec_image_provider_registered() is True
        assert m001_ip._task_spec_image_provider is provide_task_source_image  # noqa: SLF001

        assert ensure_task_spec_image_provider_registered() is True  # 幂等短路（不重复写）
        assert m001_ip._task_spec_image_provider is provide_task_source_image  # noqa: SLF001

        m001_ip.register_task_spec_image_provider(None)  # 模拟「首次导入时 M001 侧未就绪」
        assert ensure_task_spec_image_provider_registered() is True  # 启动期自愈
        assert m001_ip._task_spec_image_provider is provide_task_source_image  # noqa: SLF001
    finally:
        m001_ip.register_task_spec_image_provider(original)  # 恢复现场，避免污染其它用例


def test_register_skips_when_m001_unavailable(monkeypatch):
    """M001 侧不可用 → `False` 且**不抛**、不阻断导入/启动。"""
    monkeypatch.setitem(sys.modules, "app.modules.m001.services.image_provider", None)

    assert ensure_task_spec_image_provider_registered() is False
