"""本地受控图片存储（契约 image_store / ASM-010）。

- 目录布局：`<root>/{family_id}/{batch_id}/{seq_no}_{photo_id}.{ext}` 与同名 `_n.jpg`。
- 文件与行同生命周期：写入失败由调用方清理；本类提供幂等删除。
- 相对路径入库（不做异地路径依赖）；对外绝不序列化路径。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

_MIME_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class ImageStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def batch_rel_dir(self, family_id: str, batch_id: str) -> Path:
        return Path(family_id) / batch_id

    def abs_path(self, rel: str | Path) -> Path:
        # 防路径穿越：只允许 root 内相对路径
        p = self.root.joinpath(rel).resolve()
        root = self.root.resolve()
        if not str(p).startswith(str(root)):
            raise ValueError("非法存储路径")
        return p

    def save_original(
        self,
        rel_dir: Path,
        *,
        seq_no: int,
        photo_id: str,
        data: bytes,
        mime: str,
    ) -> tuple[str, str]:
        """写原始图 → (相对路径, sha256)。ext 由已校验 MIME 决定（无外部文件名输入）。"""
        ext = _MIME_EXT[mime]
        name = f"{seq_no}_{photo_id}.{ext}"
        rel = rel_dir / name
        target = self.abs_path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return rel.as_posix(), hashlib.sha256(data).hexdigest()

    def save_normalized(self, rel_dir: Path, *, seq_no: int, photo_id: str, data: bytes) -> str:
        name = f"{seq_no}_{photo_id}_n.jpg"
        rel = rel_dir / name
        target = self.abs_path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return rel.as_posix()

    def read(self, rel: str) -> bytes:
        return self.abs_path(rel).read_bytes()

    def delete(self, *rel_paths: str) -> None:
        """物理删除（不存在即忽略，幂等）；失败抛 OSError 由调用方裁决。"""
        for rel in rel_paths:
            if not rel:
                continue
            target = self.abs_path(rel)
            try:
                target.unlink(missing_ok=True)
            except FileNotFoundError:
                pass
