"""Gettext-backed localization helpers for presentation UI strings.

The presentation layer owns operator-facing copy.  This module discovers
packaged gettext catalogs, exposes language options for settings, and keeps a
small active translation object for Kivy widgets that render static labels.
"""

from __future__ import annotations

from dataclasses import dataclass
import gettext
from importlib import resources
from importlib.resources.abc import Traversable
from io import BytesIO

DEFAULT_UI_LANGUAGE = "en"
TRANSLATION_DOMAIN = "polyglot_site_translator"
LOCALE_PACKAGE = "polyglot_site_translator.presentation.locale"


@dataclass(frozen=True)
class UILanguageOption:
    """Selectable UI language discovered from packaged gettext catalogs.

    Attributes:
        value:
            Persisted language code used by app settings.
        label:
            Display label translated by the language's own catalog.
    """

    value: str
    label: str


_ACTIVE_TRANSLATION: gettext.NullTranslations = gettext.NullTranslations()
_PREFIX_MSGIDS = (
    "Open ",
    "Status: ",
    "Findings: ",
    "Processed families: ",
    "Current file: ",
    "Current entry: ",
    "Downloading remote file ",
    "Uploading local file ",
    "Preparing local workspace at ",
    "Created local workspace directories under ",
    "Listing local files under ",
    "Discovered local file ",
    "Discovered remote file ",
    "Running translation workflow for locales: ",
)
_FRAGMENT_MSGIDS = (
    "Project-scoped translation workflow summary and prepared locale families.",
    "Project-scoped audit overview and normalized findings summary.",
    "Remote connection: none configured",
    "Remote connection: None",
    "Framework detection:",
    "No framework detected.",
    "No supported framework markers were detected.",
    "manage.py is present at the project root.",
    "settings.py was found in the Django configuration package.",
    "wsgi.py was found in the Django configuration package.",
    "asgi.py was found in the Django configuration package.",
    "locale/ directory is present.",
    "Partial Django evidence was found, but manage.py and a settings entrypoint "
    "were not both available.",
    "wp-config.php is present at the project root.",
    "wp-content/ is present.",
    "wp-includes/ is present.",
    "wp-admin/ is present.",
    "Partial WordPress evidence was found, but the layout is insufficient to "
    "confirm the framework.",
    "app.py contains Flask application markers.",
    "wsgi.py contains Flask application markers.",
    "app/__init__.py contains Flask factory markers.",
    "babel.cfg is present.",
    "translations/ directory is present.",
    "Partial Flask evidence was found, but the project layout is insufficient "
    "to confirm the framework.",
    "Connection type:",
    "Remote user:",
    "Framework:",
    "Locale:",
    "Compile MO:",
    "External translator:",
    "Translation cache:",
    "Only fuzzy:",
    "Dry-run:",
    "Stats only:",
    "Report inconsistencies:",
    "Remote:",
    "Path:",
    "Sync mode:",
    "Actions:",
    "Files:",
    "Error Code:",
    "Families:",
    "Progress:",
    "Completed entries:",
    "Files found:",
    "Families found:",
    "Families processed:",
    "PO files discovered:",
    "Total entries:",
    "Missing entries:",
    "Fuzzy entries:",
    "Completed from initial sync:",
    "Reused from other variant:",
    "Synchronized entries:",
    "Translated entries:",
    "Translated from cache:",
    "Translated via provider:",
    "Skipped by sync-only:",
    "Failed entries:",
    "Written PO files:",
    "Compiled MO files:",
    "Translation cache path:",
    "Translation inconsistencies:",
    "Variant differences found:",
    "Variant difference details:",
    "Failed items:",
    "Failed MO files:",
    "Families processed:",
    "Compiled MO files:",
    "PO processing service is not configured in this runtime.",
    "Local workspace is empty. No files were uploaded.",
    "Remote workspace is empty. No files were downloaded.",
    "Downloaded",
    "Uploaded",
    "files into",
    "files from",
    "django_adapter",
    "wordpress_adapter",
    "flask_adapter",
    "Translation",
    "Sync",
    "Audit",
    "enabled",
    "disabled",
    "filtered",
    "full",
    "running",
    "completed",
    "completed_with_errors",
    "failed",
    "Active",
    "Inactive",
)


def available_ui_language_options() -> list[UILanguageOption]:
    """Return selectable UI languages discovered from packaged catalogs.

    Returns:
        value:
            Stable language options sorted with English first.
    """
    options = [
        UILanguageOption(value=language_code, label=_language_label(language_code))
        for language_code in _discover_language_codes()
    ]
    return sorted(options, key=_language_sort_key)


def is_supported_ui_language(language_code: str) -> bool:
    """Return whether ``language_code`` has a packaged gettext catalog.

    Args:
        language_code:
            Persisted UI language code to validate.

    Returns:
        value:
            ``True`` when a matching ``.mo`` catalog is packaged.
    """
    return language_code in set(_discover_language_codes())


def build_translation(language_code: str) -> gettext.NullTranslations:
    """Load the gettext translation for a supported UI language.

    Args:
        language_code:
            Persisted UI language code.

    Returns:
        value:
            GNU gettext translations loaded from packaged ``.mo`` bytes.

    Raises:
        ValueError:
            Raised when no packaged catalog exists for ``language_code``.
    """
    mo_file = _catalog_file(language_code, "mo")
    if not mo_file.is_file():
        msg = f"Unsupported UI language: {language_code}"
        raise ValueError(msg)
    return gettext.GNUTranslations(BytesIO(mo_file.read_bytes()))


def set_active_ui_language(language_code: str) -> None:
    """Set the active UI language used by ``tr``.

    Args:
        language_code:
            Persisted UI language code.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ValueError:
            Raised when no packaged catalog exists for ``language_code``.
    """
    global _ACTIVE_TRANSLATION  # noqa: PLW0603
    _ACTIVE_TRANSLATION = build_translation(language_code)


def tr(message: str) -> str:
    """Translate a UI string through the active gettext catalog.

    Args:
        message:
            English source string used as gettext ``msgid``.

    Returns:
        value:
            Translated string for the active UI language.
    """
    return _ACTIVE_TRANSLATION.gettext(message)


def tr_ui_text(message: str) -> str:
    """Translate static fragments inside visible UI text.

    Args:
        message:
            English source text, possibly with dynamic project names, paths,
            statuses, or service-provided values around static labels.

    Returns:
        value:
            Text translated for known UI fragments while preserving dynamic
            values that should not be treated as gettext message ids.
    """
    translated = tr(message)
    if translated != message:
        return translated
    for prefix in _PREFIX_MSGIDS:
        if message.startswith(prefix):
            return f"{tr(prefix)}{tr_ui_text(message[len(prefix) :])}"
    for fragment in _FRAGMENT_MSGIDS:
        translated_fragment = tr(fragment)
        if translated_fragment != fragment:
            translated = translated.replace(fragment, translated_fragment)
    via_label = tr("via")
    if via_label != "via":
        translated = translated.replace(" via ", f" {via_label} ")
    return translated


def _discover_language_codes() -> tuple[str, ...]:
    """Discover language directories that contain compiled UI catalogs.

    Returns:
        value:
            Language codes with packaged ``.mo`` files.
    """
    locale_root = resources.files(LOCALE_PACKAGE)
    language_codes = [
        language_dir.name
        for language_dir in locale_root.iterdir()
        if language_dir.is_dir() and _catalog_file(language_dir.name, "mo").is_file()
    ]
    return tuple(language_codes)


def _catalog_file(language_code: str, suffix: str) -> Traversable:
    """Return the catalog file traversable for a language and suffix.

    Args:
        language_code:
            Language code directory under the packaged locale root.
        suffix:
            Catalog suffix, such as ``"po"`` or ``"mo"``.

    Returns:
        value:
            Traversable pointing at the requested catalog file.
    """
    return (
        resources.files(LOCALE_PACKAGE)
        / language_code
        / "LC_MESSAGES"
        / f"{TRANSLATION_DOMAIN}.{suffix}"
    )


def _language_label(language_code: str) -> str:
    """Return the self-localized label for a language.

    Args:
        language_code:
            Language code with a packaged catalog.

    Returns:
        value:
            Label rendered in the language selector.
    """
    return build_translation(language_code).gettext("language.name")


def _language_sort_key(option: UILanguageOption) -> tuple[int, str]:
    """Return a stable sort key for language options.

    Args:
        option:
            Language option to sort.

    Returns:
        value:
            Sort key that keeps English first and other languages alphabetical.
    """
    return (0 if option.value == DEFAULT_UI_LANGUAGE else 1, option.label)
