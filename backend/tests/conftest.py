"""测试公共 fixture：每用例独立 SQLite 临时库；双家庭 world 用于越权矩阵。

遵循 MODULE_TEST：每用例独立库（临时文件），避免用例间污染；
schools 用默认 seed（幂等），primary 起步 + junior/senior 样例供过滤断言。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

PW = "Passw0rd1"

# 部署侧 backend/.env 可能写入真实三方 AI 密钥（联调）。测试必须与其隔离：
# 始终按「无凭据 + auto + 允许兜底」解析 → 离线 Mock，保证确定性与可重复（Mock 为最低验收线）。
_AI_CREDENTIAL_KEYS = (
    "AT_AI_LLM_MODEL",
    "AT_AI_LLM_API_KEY",
    "AT_AI_LLM_BASE_URL",
    "AT_AI_VISION_MODEL",
    "AT_AI_VISION_API_KEY",
    "AT_AI_VISION_BASE_URL",
    "AT_AI_OCR_MODEL",
    "AT_AI_OCR_API_KEY",
    "AT_AI_OCR_BASE_URL",
)


@pytest.fixture(autouse=True)
def isolate_deploy_config(monkeypatch):
    """隔离部署侧 backend/.env（真实 AI 密钥 / 质检放宽项）。

    - 关闭 dotenv 读取 → 测试始终用契约默认值（如质检默认阈值）；
    - 清空 OS 级 AI 凭据兜底 → 始终离线 Mock；
    - 清理 Provider/设置缓存；用例后复原。
    """
    from app.core.ai.config import AISettings, get_ai_settings
    from app.core.ai.service import get_ai_service
    from app.core.config import Settings
    from app.modules.m002.config import M002Settings, get_m002_settings

    for cls in (Settings, AISettings, M002Settings):
        cls.model_config["env_file"] = None

    monkeypatch.setenv("AT_AI_PROVIDER_MODE", "auto")
    monkeypatch.setenv("AT_AI_ALLOW_MOCK_FALLBACK", "true")
    for key in _AI_CREDENTIAL_KEYS:
        monkeypatch.setenv(key, "")
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()
    get_m002_settings.cache_clear()
    yield
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()
    get_m002_settings.cache_clear()


def _make_settings(tmp_path) -> Settings:
    return Settings(
        database_url="sqlite:///" + (tmp_path / "test.db").as_posix(),
        frontend_dir=str(tmp_path / "no_frontend"),  # 测试不需要挂载静态
        scrypt_n=2**10,  # 测试提速：降低 scrypt 代价（单向性不变）
        scrypt_r=8,
        scrypt_p=1,
    )


@pytest.fixture
def client(tmp_path):
    app = create_app(_make_settings(tmp_path), mount_frontend=False)
    with TestClient(app) as c:  # 触发 lifespan：建表 + seed
        yield c


@pytest.fixture
def factory(client):
    """与 client 同库的 sessionmaker（集成/内部服务测试用）。"""
    return client.app.state.session_factory


def register_family(client, login: str) -> dict:
    resp = client.post(
        "/api/v1/family/register",
        json={"login_name": login, "password": PW, "display_name": f"{login} 家庭"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def login_family(client, login: str) -> str:
    resp = client.post("/api/v1/family/login", json={"login_name": login, "password": PW})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def world(client):
    """双家庭环境（family A 与 family B）+ 学校字典首条 primary 学校。"""
    fa = register_family(client, "family_a")
    fb = register_family(client, "family_b")
    ta = login_family(client, "family_a")
    tb = login_family(client, "family_b")
    schools = client.get("/api/v1/schools", headers=auth(ta)).json()["items"]
    primary = [s for s in schools if s["stage"] == "primary"][0]
    return {
        "client": client,
        "family_id_a": fa["family_id"],
        "family_id_b": fb["family_id"],
        "ha": auth(ta),
        "hb": auth(tb),
        "token_a": ta,
        "schools": schools,
        "school_primary": primary,
    }


def create_student(client, headers: dict, *, school_id: str, name: str = "小明") -> dict:
    resp = client.post(
        "/api/v1/students",
        json={"name": name, "grade_level": "三年级", "school_id": school_id, "relation": "儿子"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def valid_task_payload(student_id: str, **overrides) -> dict:
    payload = {
        "title": "数学口算 20 题",
        "subject": "math",
        "grade_level": "三年级",
        "content": "课本 P23 练习",
        "student_id": student_id,
        "deadline": "2026-09-10T20:00:00Z",
        "items": [
            {"seq": 1, "item_type": "objective", "subject": "math", "stem": "12 x 8 = ?", "reference_answer": "96"},
            {"seq": 2, "item_type": "subjective", "subject": "math", "stem": "写出计算过程", "reference_answer": None},
        ],
    }
    payload.update(overrides)
    return payload


def create_task(client, headers: dict, payload: dict) -> dict:
    resp = client.post("/api/v1/tasks", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
