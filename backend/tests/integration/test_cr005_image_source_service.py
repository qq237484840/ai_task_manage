"""集成级（真实装配）：`CR-005` 图片源解析的**服务级**取证（`Task-021` 验收）。

核心结论（**不依赖业务桩**；仅「判据开关」与「观测桩」）：

1. **跨家庭越权取图被真实阻断**：家庭 B 的任务引用家庭 A 的 `photo_id` → M002 真实
   `provide_task_source_image` 以 **B 的 `family_id`** 查询 → `None` → 图片源**不转发**
   → `placeholder` + `contents==[]`（`ingest` 与 `reparse` 两条路径一致）；
2. **对照（本家）**：同一 `photo_id` 由**照片所属家庭**引用 → 图片源**被转发**
   （观测桩捕获 `sources`，`image.path` 位于受控根内）。

**桩说明（PM 铁律 ①）**：
- `task_parser._vision_is_real` 被替换为恒 `True` —— 测试环境**无真实三方凭据**，无法令真实判据为真；
  该函数是「是否真实 Vision」的**开关**，非业务逻辑；
- 捕获 `sources` 的 parser 为**观测桩**（记录入参、返回 `None`），**不参与结论判定**；
- 照片行走**真实 `PhotoRepository`** + 真实 `ImageStore` 落盘（同 `test_m002_task_source_image.py`）。

**真机补充证据**：本文件结论亦在**真实服务（8010，真实 Vision）**上取得一次（见 `Task-021 §5` ③）：
跨家庭 → `201` 建单但 `placeholder / 0 项`（不转发）；本家 → `parsed / 4 项` +
DATA-009 `task_spec_parse / qwen3.8-flash / mock=0 / status=ok`。

**登记项（只登记不修，`Task-021 §6`）**：实测 **M001 `ingest` 不校验 `photo_id` 归属**（跨家庭引用
返回 `201`）→ 防越权**仅由 M002 provider 这一道**保证；若未来新增图片源消费面（如缩略图渲染），
需另行评估。→ 由 PM 分配 `TD-*` / `RISK-*` ID。
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.modules.m001.services import image_provider as ip
from app.modules.m001.services import task_parser
from app.modules.m002.clients.task_client import provide_task_source_image
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.services.image_store import ImageStore
from tests._m001_helpers import (
    DAY,
    TEST_TERM_START,
    create_task_v2,
    install_fixed_window,
    task_payload,
)
from tests.conftest import create_student


@pytest.fixture
def image_root(tmp_path, monkeypatch):
    """M002 图片根目录 → 临时目录（并清缓存，避免跨用例泄漏）。"""
    from app.modules.m002.config import get_m002_settings

    root = tmp_path / "images"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AT_M002_IMAGE_STORE_ROOT", str(root))
    get_m002_settings.cache_clear()
    yield root
    get_m002_settings.cache_clear()


@pytest.fixture
def real_vision(monkeypatch):
    """判据开关：令 `_vision_is_real()` 为真（见模块 docstring 桩说明）。"""
    monkeypatch.setattr(task_parser, "_vision_is_real", lambda: True)


@pytest.fixture
def real_provider():
    """注册**真实** M002 provider（退出时恢复原槽位，避免污染其它用例）。"""
    original = ip._task_spec_image_provider  # noqa: SLF001 - 契约槽位现场恢复
    ip.register_task_spec_image_provider(provide_task_source_image)
    yield
    ip.register_task_spec_image_provider(original)


@pytest.fixture
def spy_parser(monkeypatch):
    """观测桩：记录 `sources` 入参并返回 `None`（不产出草稿，不影响结论）。"""
    captured: dict = {}

    def _spy(session, *, family_id=None, sources=None, **kwargs):  # noqa: ARG001
        captured["sources"] = sources
        return None

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: _spy)
    return captured


def _seed_photo(world, factory, image_root: Path, *, family_key: str = "family_id_a") -> str:
    """在指定家庭名下落 1 张真实照片行 + 真实文件（批次经**真实 API** 创建，满足外键）。"""
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小P")
    batch_id = c.post(
        "/api/v1/upload-batches",
        json={"student_id": stu["student_id"], "kind": "task_spec"},
        headers=ha,
    ).json()["batch_id"]
    photo_id = str(uuid.uuid4())
    fam = world[family_key]
    store = ImageStore(image_root)
    rel = store.save_normalized(
        store.batch_rel_dir(fam, batch_id), seq_no=1, photo_id=photo_id, data=b"\xff\xd8\xff\xd9"
    )
    with factory() as s:
        PhotoRepository.create(
            s,
            photo_id=photo_id,
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
    return photo_id


def test_cross_family_photo_is_not_forwarded(
    world, factory, image_root, real_vision, real_provider, spy_parser
):
    """**服务级防越权（无业务桩）**：跨家庭 `photo_id` → provider 以本家 `family_id` 查 → `None` → 不转发。"""
    c = world["client"]
    photo_a = _seed_photo(world, factory, image_root, family_key="family_id_a")
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu_b = create_student(
        c, world["hb"], school_id=world["school_primary"]["school_id"], name="小B"
    )

    task = create_task_v2(
        c,
        world["hb"],
        task_payload(stu_b["student_id"], sources=[{"seq": 1, "kind": "image", "photo_id": photo_a}]),
    )
    spy_parser.clear()  # 只观测 `reparse` 这一次

    r = c.post(f"/api/v1/tasks/{task['task_id']}/reparse", headers=world["hb"])

    assert r.status_code == 200, r.text
    assert r.json()["spec_status"] == "placeholder", "跨家庭图片源不得转发（防越权取图）"
    assert r.json()["contents"] == []
    kinds = [s.kind for s in (spy_parser.get("sources") or [])]
    assert "image" not in kinds, f"越权图片源被转发了：sources={kinds}"


def test_own_family_photo_is_forwarded(
    world, factory, image_root, real_vision, real_provider, spy_parser
):
    """**对照（本家）**：同一 `photo_id` 由照片所属家庭引用 → 图片源被转发（受控路径）。"""
    c, ha = world["client"], world["ha"]
    photo_a = _seed_photo(world, factory, image_root, family_key="family_id_a")
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu_a = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小A")

    task = create_task_v2(
        c,
        ha,
        task_payload(stu_a["student_id"], sources=[{"seq": 1, "kind": "image", "photo_id": photo_a}]),
    )
    spy_parser.clear()

    r = c.post(f"/api/v1/tasks/{task['task_id']}/reparse", headers=ha)

    assert r.status_code == 200, r.text
    sources = spy_parser.get("sources") or []
    assert [s.kind for s in sources] == ["image"], f"sources={sources}"
    assert sources[0].image is not None
    assert Path(sources[0].image.path).is_relative_to(image_root.resolve())
