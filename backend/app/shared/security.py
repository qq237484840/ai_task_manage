"""共享安全工具（契约 security：scrypt 密码哈希 + 不透明会话令牌哈希存储）。

- 密码：标准库 hashlib.scrypt，每账号随机盐，存储 `salt_hex$hash_hex$n$r$p`。
- 会话令牌：secrets.token_urlsafe(32) 原文仅签发时返回一次；库内仅存 sha256(token)。
"""
import hashlib
import hmac
import os
import secrets


def hash_password(password: str, *, n: int = 2**14, r: int = 8, p: int = 1, dklen: int = 32) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen, maxmem=64 * 1024 * 1024
    )
    return f"{salt.hex()}${digest.hex()}${n}${r}${p}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex, n, r, p = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    try:
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=64 * 1024 * 1024,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
