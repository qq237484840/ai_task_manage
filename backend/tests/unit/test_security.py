"""单测：密码哈希（scrypt）与会话令牌哈希。"""

from app.shared.security import hash_password, hash_token, new_session_token, verify_password


def test_hash_password_verify_ok():
    h = hash_password("Passw0rd1")
    assert verify_password("Passw0rd1", h) is True
    assert verify_password("Passw0rd2", h) is False


def test_hash_password_salt_randomness():
    assert hash_password("Passw0rd1") != hash_password("Passw0rd1")


def test_verify_password_garbage_is_false():
    assert verify_password("Passw0rd1", "not-a-valid-stored-hash") is False
    assert verify_password("", "$bad") is False


def test_token_hash_does_not_keep_plaintext():
    token = new_session_token()
    h = hash_token(token)
    assert token not in h
    assert h != token
    assert hash_token(token) == h
    assert hash_token("other") != h
