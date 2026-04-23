"""Unit tests for local site secret encryption helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyglot_site_translator.domain.site_registry.errors import SiteRegistryPersistenceError
from polyglot_site_translator.infrastructure.site_secrets import LocalKeySiteSecretCipher


def test_secret_cipher_roundtrips_plaintext_and_reuses_the_generated_key(tmp_path: Path) -> None:
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")

    encrypted = cipher.encrypt("super-secret")

    assert encrypted != "super-secret"
    assert cipher.decrypt(encrypted) == "super-secret"


def test_secret_cipher_rejects_tampered_payloads(tmp_path: Path) -> None:
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
    cipher = LocalKeySiteSecretCipher(tmp_path / "nested" / "site_registry.key")

    def fail_write_bytes(_self: Path, _data: bytes) -> int:
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(type(tmp_path / "site_registry.key"), "write_bytes", fail_write_bytes)

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Site secret key could not be loaded from",
    ):
        cipher.encrypt("super-secret")


def test_secret_cipher_rejects_invalid_encoded_payloads(tmp_path: Path) -> None:
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"Stored site secret failed integrity validation\.",
    ):
        cipher.decrypt("not-valid-base64***")
