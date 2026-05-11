"""Unit tests for local site secret encryption helpers."""

from __future__ import annotations

from base64 import urlsafe_b64encode
import hashlib
import hmac
from pathlib import Path

import pytest

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryPersistenceError,
)
from polyglot_site_translator.infrastructure.site_secrets import (
    _NONCE_SIZE,
    LocalKeySiteSecretCipher,
)


def test_secret_cipher_roundtrips_plaintext_and_reuses_the_generated_key(
    tmp_path: Path,
) -> None:
    """Verify secret cipher roundtrips plaintext and reuses the generated key.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")

    encrypted = cipher.encrypt("super-secret")

    assert encrypted != "super-secret"
    assert cipher.decrypt(encrypted) == "super-secret"


def test_secret_cipher_rejects_tampered_payloads(tmp_path: Path) -> None:
    """Verify secret cipher rejects tampered payloads.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")
    encrypted = cipher.encrypt("super-secret")
    tampered = encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B")

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Stored site secret failed integrity validation\.",
    ):
        cipher.decrypt(tampered)


def test_secret_cipher_wraps_os_errors_when_key_storage_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify secret cipher wraps os errors when key storage fails.

    Args:
        monkeypatch:
            Value supplied to this callable.
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        OSError:
            Raised when this callable hits the corresponding error path.
    """
    cipher = LocalKeySiteSecretCipher(tmp_path / "nested" / "site_registry.key")

    def fail_write_bytes(_self: Path, _data: bytes) -> int:
        """Handle fail write bytes.

        Args:
            _self:
                Value supplied to this callable.
            _data:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(
        type(tmp_path / "site_registry.key"), "write_bytes", fail_write_bytes
    )

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Site secret key could not be loaded from",
    ):
        cipher.encrypt("super-secret")


def test_secret_cipher_rejects_invalid_encoded_payloads(tmp_path: Path) -> None:
    """Verify secret cipher rejects invalid encoded payloads.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Stored site secret failed integrity validation\.",
    ):
        cipher.decrypt("not-valid-base64***")


def test_secret_cipher_rejects_non_ascii_ciphertext(tmp_path: Path) -> None:
    """Verify secret cipher rejects non ascii ciphertext.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Stored site secret could not be decoded\.",
    ):
        cipher.decrypt("secreto-ñ")


def test_secret_cipher_rejects_invalid_utf8_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify secret cipher rejects invalid utf8 plaintext.

    Args:
        tmp_path:
            Value supplied to this callable.
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")
    key = b"k" * 32
    nonce = b"n" * _NONCE_SIZE
    encrypted = b"x"
    mac = hmac.new(key, nonce + encrypted, hashlib.sha256).digest()
    payload = urlsafe_b64encode(nonce + mac + encrypted).decode("ascii")

    monkeypatch.setattr(cipher, "_load_or_create_key", lambda: key)
    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.site_secrets._xor_bytes",
        lambda _left, _right: b"\xff",
    )

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Stored site secret could not be decoded\.",
    ):
        cipher.decrypt(payload)
