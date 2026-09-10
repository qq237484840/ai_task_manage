"""受控取图响应：Range 支持（单区间 bytes；多/非法区间回退全量 200）。"""
from __future__ import annotations

import re

from fastapi import Request
from fastapi.responses import Response

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def photo_content_response(
    request: Request, data: bytes, media_type: str
) -> Response:
    total = len(data)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": media_type,
        "Content-Length": str(total),
    }
    range_header = request.headers.get("range", "").strip()
    if range_header and total > 0:
        m = _RANGE_RE.match(range_header)
        if m:
            start_raw, end_raw = m.groups()
            try:
                if start_raw == "":  # bytes=-N：最后 N 字节
                    suffix = int(end_raw)
                    if suffix <= 0:
                        raise ValueError
                    start, end = max(total - suffix, 0), total - 1
                else:
                    start = int(start_raw)
                    end = int(end_raw) if end_raw else total - 1
                    end = min(end, total - 1)
            except ValueError:
                start, end = None, None
            if start is not None:
                if start > end:
                    return Response(
                        status_code=416,
                        headers={"Content-Range": f"bytes */{total}"},
                    )
                body = data[start : end + 1]
                headers.update(
                    {
                        "Content-Range": f"bytes {start}-{end}/{total}",
                        "Content-Length": str(len(body)),
                    }
                )
                return Response(content=body, status_code=206, headers=headers)
    return Response(content=data, status_code=200, headers=headers)
