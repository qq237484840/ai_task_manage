"""Prompt 资产集中管理（ADR-003：Prompt 集中管理并版本化，禁止散落业务代码）。

- 资产文件命名 `key.version.txt`（如 `task_spec_parse.v1.txt`）；
- 版本标识随 `PromptTemplate.version` 写入 DATA-009 `prompt_version`；
- 渲染使用 `string.Template`（`$var`），避免与 JSON 花括号冲突。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template

_PROMPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PromptTemplate:
    key: str
    version: str
    text: str

    def render(self, **values: object) -> str:
        """以 `$name` 占位渲染；缺失变量留空（避免因可选上下文缺省而抛错）。"""
        safe = {k: ("" if v is None else str(v)) for k, v in values.items()}
        return Template(self.text).safe_substitute(safe)


def _split_name(filename: str) -> tuple[str, str]:
    stem = filename[:-4] if filename.endswith(".txt") else filename
    key, _, version = stem.rpartition(".")
    if not key or not version:
        raise ValueError(f"prompt 资产命名必须为 key.version.txt：{filename}")
    return key, version


@lru_cache
def load_prompts() -> dict[str, PromptTemplate]:
    """加载 `prompts/*.txt`（进程内缓存）；相同 key 多版本时取文件名排序最后者。"""
    registry: dict[str, PromptTemplate] = {}
    for path in sorted(_PROMPT_DIR.glob("*.txt")):
        key, version = _split_name(path.name)
        registry[key] = PromptTemplate(
            key=key, version=version, text=path.read_text(encoding="utf-8")
        )
    return registry


def get_prompt(key: str) -> PromptTemplate:
    try:
        return load_prompts()[key]
    except KeyError as exc:  # pragma: no cover - 资产缺失属装配错误
        raise KeyError(f"未登记的 prompt 资产：{key}") from exc


PROMPT_TASK_SPEC_PARSE = "task_spec_parse"
PROMPT_PHOTO_LINK_SUGGEST = "photo_link_suggest"
PROMPT_COMPLETION_ANALYSIS = "completion_analysis"
PROMPT_OCR_EXTRACT = "ocr_extract"

__all__ = [
    "PROMPT_COMPLETION_ANALYSIS",
    "PROMPT_OCR_EXTRACT",
    "PROMPT_PHOTO_LINK_SUGGEST",
    "PROMPT_TASK_SPEC_PARSE",
    "PromptTemplate",
    "get_prompt",
    "load_prompts",
]
