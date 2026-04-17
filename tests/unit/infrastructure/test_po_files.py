"""Unit tests for PO file infrastructure helpers."""

from __future__ import annotations

import polib
import pytest

from polyglot_site_translator.infrastructure.po_files import _domain_msgstr_plural_from_polib


def test_domain_msgstr_plural_from_polib_dict_int_keys() -> None:
    entry = polib.POEntry(
        msgid="file",
        msgid_plural="files",
        msgstr_plural={0: "archivo", 1: "archivos"},
    )
    assert _domain_msgstr_plural_from_polib(entry) == {
        "0": "archivo",
        "1": "archivos",
    }


def test_domain_msgstr_plural_from_polib_list_positions() -> None:
    entry = polib.POEntry(msgid="x")
    object.__setattr__(entry, "msgstr_plural", ["a", "b"])
    assert _domain_msgstr_plural_from_polib(entry) == {"0": "a", "1": "b"}


def test_domain_msgstr_plural_from_polib_empty_dict() -> None:
    entry = polib.POEntry(msgid="x", msgstr_plural={})
    assert _domain_msgstr_plural_from_polib(entry) == {}


def test_domain_msgstr_plural_from_polib_rejects_unsupported_type() -> None:
    entry = polib.POEntry(msgid="odd")
    object.__setattr__(entry, "msgstr_plural", 99)
    with pytest.raises(TypeError, match="Unexpected msgstr_plural type"):
        _domain_msgstr_plural_from_polib(entry)
