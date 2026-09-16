"""链路 T 解析适配（M001 侧）—— 经 `app/core/ai/` 调用，内置 Mock 兜底（ADR-011）。

- 真实入口：`app/core/ai/`（执行方 `AGENT-AI`/Task-006），运行时可用则优先调用；
- **Mock 兜底为最低验收线**：`app.core.ai` 未就绪 → 使用本地启发式解析（文本源 → 学科 + 内容项），
  图片源在 Mock 下不产生草稿（无法 OCR）；返回 `None` 表示"无可落库草稿"，上层保持 `placeholder`；
- 解析失败/超时/返回不合规 → 返回 `None`，**不污染事实层**（契约 §F1 降级）。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 建议学科值（ASM-011，不写死）：中文标签 → 英文标签
_SUBJECT_ALIASES: dict[str, str] = {
    "语文": "chinese",
    "数学": "math",
    "英语": "english",
    "英文": "english",
    "科学": "science",
    "物理": "physics",
    "化学": "chemistry",
    "生物": "biology",
    "历史": "history",
    "地理": "geography",
    "政治": "politics",
    "道法": "morality",
    "道德与法治": "morality",
    "chinese": "chinese",
    "math": "math",
    "english": "english",
    "science": "science",
}

_DEFAULT_SUBJECT = "other"
_LABEL_RE = re.compile(r"^\s*([\u4e00-\u9fa5A-Za-z]{1,10})\s*[:：]\s*(.+)$")
_SPLIT_RE = re.compile(r"[\n\r；;]+")
_MAX_SEGMENT = 2000


@dataclass(frozen=True)
class ContentDraft:
    """解析草稿：一条内容项（学科 + 文本）。"""

    subject: str
    text: str


class Parser(Protocol):
    """解析器调用约定（`Task-012` §3.5：调用方式统一，**禁止**按旧签名静默兼容）。

    - 位置参数：`sources: list[dict]`（M001 输入源）；
    - 关键字参数：`session: Session | None = None`（传请求会话 → 落 DATA-009 `ai_call_records`）；
      `family_id: str | None = None`（`CR-005`：图片源经回调槽读取时的家庭上下文；
      缺省 `None` 不影响文本源路径）。
    """

    def __call__(
        self,
        sources: list[dict],
        *,
        session: "Session | None" = None,
        family_id: str | None = None,
    ) -> "list[ContentDraft] | None": ...


def _normalize_subject(raw: str) -> str:
    key = raw.strip().lower()
    return _SUBJECT_ALIASES.get(key, key or _DEFAULT_SUBJECT)


def mock_parse_sources(sources: list[dict]) -> list[ContentDraft] | None:
    """本地启发式解析：按行/分号切分文本源，识别「学科：内容」标签。"""
    drafts: list[ContentDraft] = []
    for src in sources:
        if src.get("kind") != "text":
            continue  # Mock 无法 OCR 图片
        raw = (src.get("text_content") or "").strip()
        if not raw:
            continue
        for segment in _SPLIT_RE.split(raw):
            segment = segment.strip()
            if not segment:
                continue
            match = _LABEL_RE.match(segment)
            if match:
                subject = _normalize_subject(match.group(1))
                text = match.group(2).strip()
            else:
                subject = _DEFAULT_SUBJECT
                text = segment
            if not text:
                continue
            drafts.append(ContentDraft(subject=subject, text=text[:_MAX_SEGMENT]))
    return drafts or None


def _iter_texts(item: Any) -> list[str] | None:
    """提取单个「解析学科项」（dict / 对象）的文本列表；结构不合规返回 None。

    兼容三种内容项形状：`str`、`dict{"text": ...}`、对象（`.text`，如 `ParsedContentItem`）。
    """
    if isinstance(item, dict):
        contents: Any = item.get("contents")
        if contents is None:
            contents = [item["text"]] if item.get("text") else []
    else:
        contents = getattr(item, "contents", None)
        if contents is None:
            single = getattr(item, "text", None)
            contents = [single] if single else []
    if not isinstance(contents, list):
        return None
    texts: list[str] = []
    for content in contents:
        if isinstance(content, str):
            value: Any = content
        elif isinstance(content, dict):
            value = content.get("text")
        else:
            value = getattr(content, "text", None)
        if isinstance(value, str) and value.strip():
            texts.append(value.strip())
    return texts


def _coerce_draft(raw: Any) -> list[ContentDraft] | None:
    """把 AI 返回（`TaskParseOutcome` / 对象 / dict）规整为草稿列表；不合规返回 None。"""
    if raw is None:
        return None
    items: Any = raw
    if hasattr(raw, "subjects"):
        items = raw.subjects
    if not isinstance(items, list):
        return None
    out: list[ContentDraft] = []
    for it in items:
        if isinstance(it, ContentDraft):
            out.append(it)
            continue
        subject = it.get("subject") if isinstance(it, dict) else getattr(it, "subject", None)
        if not subject:
            return None
        texts = _iter_texts(it)
        if texts is None:
            return None
        for text in texts:
            out.append(ContentDraft(subject=_normalize_subject(str(subject)), text=text))
    return out or None


def _ai_parser() -> Any:
    """延迟探测 `app/core/ai/` 的任务解析入口；未就绪返回 None（不抛错）。"""
    try:
        import app.core.ai as ai  # type: ignore
    except Exception:
        return None
    parser = getattr(ai, "parse_task_spec", None)
    if parser is None:
        try:
            from app.core.ai.task_spec import parse_task_spec as parser  # type: ignore
        except Exception:
            return None
    return parser


def _vision_is_real() -> bool:
    """Vision Provider 是否为**真实**（非 Mock / 非 degraded）—— 图片源转发的前置判据。

    `CR-005` 硬约束：Mock / degraded 下**不转发图片源**（Mock 无视觉能力，会产出占位草稿
    冒充解析结果 —— `BUG-004` 教训）。判据取自 `app/core/ai` 的**装配结果**
    （`ResolvedProvider.reason == "real"`），**禁止硬编码模型名**；
    AI 层不可读 → `False`（保守不转发）。
    """
    try:
        from app.core.ai.service import get_ai_service

        vision = get_ai_service().providers.vision
        return bool(vision.reason == "real") and not vision.mock and not vision.degraded
    except Exception as exc:  # noqa: BLE001 - 判定不了就不转发（保守）
        logger.warning("task_parser: 无法判定 Vision Provider 真实性（%s）→ 不转发图片源", exc)
        return False


def _to_ai_sources(
    sources: list[dict], *, session: Any = None, family_id: str | None = None
) -> list[Any]:
    """把 M001 输入源（`list[dict]`）适配为 `app/core/ai` 的 `SourceInput`。

    - **文本源**：`SourceInput.text_of(...)`；空文本不转发（行为与既有版本一致）；
    - **图片源**（`CR-005`）：仅当 ① **Vision Provider 为真实**（`_vision_is_real()`）
      ② `session` 与 `family_id` 可用 ③ M002 已注册回调槽时，经 `get_task_source_image(...)`
      取受控 `abs_path` → `SourceInput.image_of(ImageInput(mime, path, image_id=photo_id))`；
    - **任一条件不满足或取图失败 → 不转发该源**（保持 `placeholder`，**绝不伪造草稿**）。

    延迟 import（`app/core/ai/` 可能未就绪），失败由调用方兜底。
    """
    from app.core.ai.types import ImageInput, SourceInput
    from app.modules.m001.services.image_provider import get_task_source_image

    out: list[Any] = []
    for src in sources:
        kind = src.get("kind")
        if kind == "text":
            text = (src.get("text_content") or "").strip()
            if text:
                out.append(SourceInput.text_of(text))
            continue
        if kind != "image":
            continue
        photo_id = src.get("photo_id")
        if not photo_id or session is None or not family_id:
            continue  # 无上下文/无引用 → 不转发（不伪造）
        if not _vision_is_real():
            continue  # Mock / degraded → 不转发（CR-005 硬约束）
        ref = get_task_source_image(session, family_id, str(photo_id))
        if ref is None:
            continue  # 槽未注册 / 取图失败 → 不转发
        out.append(
            SourceInput.image_of(
                ImageInput(mime=ref.mime, path=ref.abs_path, image_id=str(photo_id))
            )
        )
    return out


def _mock_fallback_allowed() -> bool:
    """AI 解析失败时是否允许回落本地启发式（服从部署侧配置语义，`BUG-006` / `Task-016`）。

    判定顺序：
    1. `provider_mode=mock`（**显式 Mock = 非降级**）→ 允许；
    2. 否则取 `allow_mock_fallback`（`real` + 禁兜底 → **不允许**，须如实失败）；
    3. 配置层不可读（`app/core/ai` 未就绪）→ **保守允许** + `logger.warning`（向后兼容；
       配置不可用时无从得知部署意图，不新增静默失败面）。

    延迟 import 遵循本文件既有约定（见 `_ai_parser`）。
    """
    try:
        from app.core.ai.config import PROVIDER_MODE_MOCK, get_ai_settings

        settings = get_ai_settings()
        mode = (settings.provider_mode or "").strip().lower()
        if mode == PROVIDER_MODE_MOCK:
            return True  # 显式 Mock：本地启发式即预期路径，非降级
        return bool(settings.allow_mock_fallback)
    except Exception as exc:  # noqa: BLE001 - 配置层不可用不阻断事实层
        logger.warning("task_parser: 无法读取 AI 配置（%s）→ 按允许 Mock 兜底处理", exc)
        return True


def default_parser(
    sources: list[dict],
    *,
    session: "Session | None" = None,
    family_id: str | None = None,
) -> list[ContentDraft] | None:
    """默认解析器：优先 `app/core/ai/`；失败/未就绪时**按配置**决定是否回退 Mock（降级可观测）。

    `BUG-006` 修复：是否回落本地启发式由 `_mock_fallback_allowed()` 决定 ——
    `real` + `AT_AI_ALLOW_MOCK_FALLBACK=false` 时返回 `None`（上层保持 `placeholder`），
    不再以本地草稿冒充 AI 解析结果（`provider_mode=mock` / 允许兜底时行为不变）。

    `session` 为可选 `app/core/database` 会话：传入时 AI 调用记录（DATA-009）落条，
    便于「证明 AI 真跑」；不传（默认 `None`）则纯计算调用、不落库。

    `family_id`（`CR-005`）：图片源经回调槽受控读取所需的家庭上下文；缺省 `None` 时
    **图片源不转发**（文本源路径不受影响）。
    """
    ai_sources = _to_ai_sources(sources, session=session, family_id=family_id)
    parser = _ai_parser() if ai_sources else None
    if parser is not None:
        try:
            # 注意：模块级便捷入口签名为 `parse_task_spec(session, **kwargs)` —— `session`
            # 走位置参数，`sources` 必须走**关键字**（`AIService.parse_task_spec` 为 keyword-only）。
            outcome = parser(session, sources=ai_sources)
            coerced = _coerce_draft(outcome)
            if coerced is not None:
                return coerced
        except Exception as exc:  # noqa: BLE001 - 解析异常不阻断事实层（契约 Failure Behavior）
            logger.warning("task_parser: 核心 AI 解析降级（%s）", exc)

    if not _mock_fallback_allowed():
        logger.warning(
            "task_parser: AI 解析不可用且 Mock 兜底已禁用（allow_mock_fallback=false）→ 保持 placeholder"
        )
        return None
    return mock_parse_sources(sources)
