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
    - 关键字参数：`session: Session | None = None`（传请求会话 → 落 DATA-009 `ai_call_records`）。
    """

    def __call__(
        self, sources: list[dict], *, session: "Session | None" = None
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


def _to_ai_sources(sources: list[dict]) -> list[Any]:
    """把 M001 输入源（`list[dict]`）适配为 `app/core/ai` 的 `SourceInput`。

    - **只转发文本源**：`SourceInput.text_of(...)`；空文本不转发；
    - **图片源不转发**：M001 的 `photo_id` 仅存引用（照片实体 Owner = M002，本层无字节/路径可读），
      无法构造可用的 `ImageInput`；若硬转发会在 Mock 无视觉密钥时产出占位草稿（伪造），
      故保持现状 —— 图片源由 `mock_parse_sources` 兜底为 `None` → 上层维持 `placeholder` / `contents == []`。

    延迟 import（`app/core/ai/` 可能未就绪），失败由调用方兜底。
    """
    from app.core.ai.types import SourceInput

    out: list[SourceInput] = []
    for src in sources:
        if src.get("kind") != "text":
            continue
        text = (src.get("text_content") or "").strip()
        if text:
            out.append(SourceInput.text_of(text))
    return out


def default_parser(sources: list[dict], *, session: "Session | None" = None) -> list[ContentDraft] | None:
    """默认解析器：优先 `app/core/ai/`，失败/未就绪回退 Mock（降级可观测）。

    `session` 为可选 `app/core/database` 会话：传入时 AI 调用记录（DATA-009）落条，
    便于「证明 AI 真跑」；不传（默认 `None`）则纯计算调用、不落库。
    """
    ai_sources = _to_ai_sources(sources)
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
    return mock_parse_sources(sources)
