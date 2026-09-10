"""Task-011 ④ 浏览器级验收：种子数据脚本（真实链路 + 固定时钟注入）。

在独立的 SQLite 文件上，用**同一套生产服务**（M001 聚合 + M002 图片采集）造出可被 UI 观察的数据；
随后用 `uvicorn` 在同库上启动真实服务（含 `frontend/dist` 托管）供浏览器级验收。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DB_FILE = BACKEND / "data" / "acceptance.db"
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
if DB_FILE.exists():
    DB_FILE.unlink()

os.environ["AT_DATABASE_URL"] = "sqlite:///./data/acceptance.db"
os.environ["AT_TERM_START"] = "2026-09-01"
os.environ["AT_FRONTEND_DIR"] = str(ROOT / "frontend" / "dist")
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from tests._m001_helpers import (  # noqa: E402
    create_task_v2,
    install_fixed_window,
    task_payload,
    text_source,
)
from tests.conftest import create_student  # noqa: E402
from tests.m002_support import valid_jpeg  # noqa: E402

LOGIN, PASSWORD = "acceptance", "acceptance123"
DAY = "2026-09-10"  # 周四 → day 窗口
WEEKEND = ("2026-09-11", "2026-09-12", "2026-09-13")  # 周五~周日 → 周末作业

state: dict = {"login_name": LOGIN, "password": PASSWORD, "windows": []}

with TestClient(app) as client:
    assert (
        client.post(
            "/api/v1/family/register",
            json={"login_name": LOGIN, "password": PASSWORD, "display_name": "验收家庭"},
        ).status_code
        == 201
    )
    token = client.post(
        "/api/v1/family/login", json={"login_name": LOGIN, "password": PASSWORD}
    ).json()["token"]
    ha = {"Authorization": f"Bearer {token}"}
    school_id = client.get("/api/v1/schools?page=1&page_size=100", headers=ha).json()["items"][0][
        "school_id"
    ]
    student = create_student(client, ha, school_id=school_id, name="验收学生")
    sid = student["student_id"]
    state["student_id"] = sid

    # ---- 窗口 1：2026-09-10（周四，day）—— 今日作业
    install_fixed_window(client, DAY, term_start="2026-09-01")
    create_task_v2(
        client,
        ha,
        task_payload(sid, sources=[text_source("数学：练习册 P23 第 1-10 题")]),
    )

    # ---- 窗口 2：2026-09-11/12/13（周五~周日，weekend）—— 周末合并
    for index, day in enumerate(WEEKEND):
        install_fixed_window(client, day, term_start="2026-09-01")
        create_task_v2(
            client,
            ha,
            task_payload(sid, sources=[text_source(f"语文：周末背诵第 {index + 1} 课")]),
        )

    groups = client.get(f"/api/v1/task-groups?student_id={sid}", headers=ha).json()
    state["groups"] = [
        {
            "group_id": g["group_id"],
            "group_key": g["group_key"],
            "window_type": g["window_type"],
            "display_name": g["display_name"],
            "subjects": [
                {"group_subject_id": s["group_subject_id"], "subject": s["subject"]}
                for s in g["subjects"]
            ],
        }
        for g in (groups["items"] if isinstance(groups, dict) else groups)
    ]

    # ---- 作业照片：3 张（作业入口 kind=homework）
    batch = client.post(
        "/api/v1/upload-batches", json={"student_id": sid, "kind": "homework"}, headers=ha
    ).json()
    photos = []
    for _ in range(3):
        resp = client.post(
            "/api/v1/photos",
            files={"file": ("hw.jpg", valid_jpeg(), "image/jpeg")},
            data={"batch_id": batch["batch_id"]},
            headers=ha,
        )
        assert resp.status_code == 201, resp.text
        photos.append(resp.json()["photo_id"])
    state["photo_ids"] = photos

    # ---- 等待上传后异步挂接建议落库（默认后台线程；Mock Provider 兜底，见 BUG-003 修复）----
    # 浏览器级剧本 5 依赖「AI 建议在列表中可见」；此轮询让种子数据确定收敛后再交给浏览器。
    deadline = time.time() + 20
    photo_items: list[dict] = []
    while time.time() < deadline:
        listing = client.get(
            f"/api/v1/photos?student_id={sid}&page=1&page_size=50", headers=ha
        ).json()
        photo_items = listing["items"] if isinstance(listing, dict) else listing
        if photo_items and all(p["status"] != "unassigned" for p in photo_items):
            break
        time.sleep(0.3)

    state["photos"] = [
        {
            "photo_id": p["photo_id"],
            "status": p["status"],
            "links": [
                {
                    "link_id": link["link_id"],
                    "group_subject_id": link["group_subject_id"],
                    "source": link["source"],
                    "confirmed": link["confirmed_at"] is not None,
                }
                for link in p["links"]
            ],
        }
        for p in photo_items
    ]
    state["gates"] = client.get(f"/api/v1/photo-gates?student_id={sid}", headers=ha).json()

    # ---- 任务详情/列表用：一条任务 id
    tasks = client.get(f"/api/v1/tasks?student_id={sid}", headers=ha).json()
    items = tasks["items"] if isinstance(tasks, dict) else tasks
    state["task_ids"] = [t["task_id"] for t in items]

print(json.dumps(state, ensure_ascii=False, indent=2))
Path(ROOT / ".e2e" / "seed_state.json").write_text(
    json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("SEED_OK")
