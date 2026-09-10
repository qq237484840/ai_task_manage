"""AI 接入层配置（Task-006 / ADR-011）。

- 环境变量前缀 `AT_AI_`（如 `AT_AI_LLM_MODEL`），支持 `.env`；覆盖既有 `AT_` 约定族。
- **禁止硬编码模型名/密钥**：所有 model / api_key / base_url 均由部署侧配置注入；
  未配置 → 真实 Provider 视为不可用 → 按 `provider_mode` 降级 Mock 并显著标注（`mock-*`）。
- 配置项清单以 **Request** 报 PM 登记 `docs/CONFIGURATION.md`（本文件不自行落库文档）。
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# 运行模式取值
PROVIDER_MODE_REAL = "real"  # 仅真实三方；不可用 → 降级信号（若允许则转 Mock 并标注）
PROVIDER_MODE_MOCK = "mock"  # 仅 Mock（测试桩 / 离线演示，非默认）
PROVIDER_MODE_AUTO = "auto"  # 默认：真实三方已配置即走 real，否则 Mock 降级


class AISettings(BaseSettings):
    """AI Provider 与调用可靠性配置。"""

    model_config = SettingsConfigDict(env_prefix="AT_AI_", env_file=".env", extra="ignore")

    # —— 运行模式（ADR-011：真实三方默认 + Mock 降级）——
    # auto（默认）= 真实三方配置齐备则走 real，否则 Mock 降级（显著标注 mock-*）
    provider_mode: str = PROVIDER_MODE_AUTO
    allow_mock_fallback: bool = True  # real 模式下三方不可用时是否允许降级 Mock
    # 离线/无外网时显式切 mock 并提示演示语义（ASM-010 修订）

    # —— 调用可靠性 ——
    request_timeout_seconds: float = 20.0  # 单次三方调用超时
    max_retries: int = 2  # 可重试错误的最大重试次数（不含首次）
    retry_backoff_seconds: float = 0.5  # 指数退避基数（第 n 次重试等待 = base * n）
    max_tokens: int = 1024  # 结构化输出上限
    temperature: float = 0.0  # 确定性优先
    mock_latency_ms: int = 0  # Mock 模拟延迟（测试默认 0，不引入时序抖动）

    # —— LLM（文本）——
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""

    # —— Vision（图片理解）——
    vision_model: str = ""
    vision_api_key: str = ""
    vision_base_url: str = ""

    # —— OCR（文字提取）——
    ocr_model: str = ""
    ocr_api_key: str = ""
    ocr_base_url: str = ""

    def provider_configured(self, kind: str) -> bool:
        """指定 Provider 是否已具备真实三方接入配置（model + api_key + base_url 齐备）。"""
        model = getattr(self, f"{kind}_model", "")
        api_key = getattr(self, f"{kind}_api_key", "")
        base_url = getattr(self, f"{kind}_base_url", "")
        return bool(model and api_key and base_url)


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()
