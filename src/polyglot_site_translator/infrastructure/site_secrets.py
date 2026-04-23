"""Local reversible encryption helpers for site registry secrets."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
import binascii
import hashlib
import hmac
from pathlib import Path
import secrets

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryPersistenceError,
)

_NONCE_SIZE = 16
_KEY_SIZE = 32
_MAC_SIZE = 32
_BLOCK_SIZE = 32


class LocalKeySiteSecretCipher:
    """Encrypt and decrypt site registry secrets using a local key file."""

    def __init__(self, key_path: Path) -> None:
        self._key_path = key_path

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext for local storage."""
        key = self._load_or_create_key()
        nonce = secrets.token_bytes(_NONCE_SIZE)
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = _xor_bytes(plaintext_bytes, _build_keystream(key, nonce, len(plaintext_bytes)))
        mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        return urlsafe_b64encode(nonce + mac + ciphertext).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a stored secret."""
        key = self._load_or_create_key()
        try:
            payload = urlsafe_b64decode(ciphertext.encode("ascii"))
        except (UnicodeEncodeError, ValueError, binascii.Error) as error:
            msg = "Stored site secret could not be decoded."
            raise SiteRegistryPersistenceError(msg) from error
        nonce = payload[:_NONCE_SIZE]
        mac = payload[_NONCE_SIZE : _NONCE_SIZE + _MAC_SIZE]
        encrypted_bytes = payload[_NONCE_SIZE + _MAC_SIZE :]
        expected_mac = hmac.new(key, nonce + encrypted_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            msg = "Stored site secret failed integrity validation."
            raise SiteRegistryPersistenceError(msg)
        plaintext_bytes = _xor_bytes(
            encrypted_bytes,
            _build_keystream(key, nonce, len(encrypted_bytes)),
        )
        try:
            return plaintext_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            msg = "Stored site secret could not be decoded."
            raise SiteRegistryPersistenceError(msg) from error

    def _load_or_create_key(self) -> bytes:
        try:
            if self._key_path.exists():
                return self._key_path.read_bytes()
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            key = secrets.token_bytes(_KEY_SIZE)
            self._key_path.write_bytes(key)
        except OSError as error:
            msg = f"Site secret key could not be loaded from {self._key_path}."
            raise SiteRegistryPersistenceError(msg) from error
        return key


def _build_keystream(key: bytes, nonce: bytes, size: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < size:
        chunks.append(hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest())
        counter += 1
    return b"".join(chunks)[:size]


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(left[index] ^ right[index] for index in range(len(left)))
