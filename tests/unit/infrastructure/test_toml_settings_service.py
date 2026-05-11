"""Unit tests for TOML-backed frontend settings persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
)
import polyglot_site_translator.infrastructure.settings as settings_module
from polyglot_site_translator.infrastructure.settings import (
    SETTINGS_FILENAME,
    TomlSettingsService,
    _resolve_posix_config_dir,
    _resolve_windows_config_dir,
    build_default_settings_service,
    resolve_user_config_dir,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import AppSettingsViewModel

SETTINGS_MODULE = cast(Any, settings_module)


def test_load_settings_returns_defaults_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    """Verify load settings returns defaults when file does not exist.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)

    settings_state = service.load_settings()

    assert settings_state.app_settings.theme_mode == "system"
    assert settings_state.app_settings.window_width == 1280
    assert settings_state.app_settings.last_opened_screen == "dashboard"


def test_load_app_settings_returns_default_persisted_settings_when_file_is_missing(
    tmp_path: Path,
) -> None:
    """Verify load app settings returns default persisted settings when file is missing.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)

    loaded_settings = service._load_app_settings()

    assert loaded_settings.database_directory == str(tmp_path)


def test_save_settings_writes_toml_and_roundtrips_values(tmp_path: Path) -> None:
    """Verify save settings writes toml and roundtrips values.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="settings",
            developer_mode=True,
            ui_language="es",
            default_project_locale="es_ES,es_AR",
            default_compile_mo=False,
            default_use_external_translator=False,
            default_use_translation_cache=False,
            default_only_fuzzy=True,
            translation_cache_path="/tmp/polyglot-cache/translation-cache",
            default_dry_run=True,
            default_stats_only=True,
            default_report_inconsistencies=True,
        )
    )

    reloaded_state = service.load_settings()

    assert saved_state.app_settings.last_opened_screen == "settings"
    assert reloaded_state.app_settings.theme_mode == "dark"
    assert reloaded_state.app_settings.window_width == 1440
    assert reloaded_state.app_settings.window_height == 900
    assert reloaded_state.app_settings.remember_last_screen is True
    assert reloaded_state.app_settings.last_opened_screen == "settings"
    assert reloaded_state.app_settings.developer_mode is True
    assert reloaded_state.app_settings.ui_language == "es"
    assert reloaded_state.app_settings.default_project_locale == "es_ES,es_AR"
    assert reloaded_state.app_settings.default_compile_mo is False
    assert reloaded_state.app_settings.default_use_external_translator is False
    assert reloaded_state.app_settings.default_use_translation_cache is False
    assert reloaded_state.app_settings.default_only_fuzzy is True
    assert (
        reloaded_state.app_settings.translation_cache_path
        == "/tmp/polyglot-cache/translation-cache"
    )
    assert reloaded_state.app_settings.default_dry_run is True
    assert reloaded_state.app_settings.default_stats_only is True
    assert reloaded_state.app_settings.default_report_inconsistencies is True
    assert 'theme_mode = "dark"' in settings_path.read_text(encoding="utf-8")


def test_save_settings_roundtrips_sync_scope_settings(tmp_path: Path) -> None:
    """Verify save settings roundtrips sync scope settings.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    service.save_settings(
        AppSettingsViewModel(
            sync_scope_settings=AdapterSyncScopeSettings(
                global_rules=(
                    ConfiguredSyncRule(
                        relative_path=".git",
                        filter_type=SyncFilterType.DIRECTORY,
                        behavior=SyncRuleBehavior.EXCLUDE,
                        description="Ignore Git metadata.",
                        is_enabled=True,
                    ),
                ),
                framework_rule_sets=(
                    FrameworkSyncRuleSet(
                        framework_type="django",
                        rules=(
                            ConfiguredSyncRule(
                                relative_path=".venv",
                                filter_type=SyncFilterType.DIRECTORY,
                                behavior=SyncRuleBehavior.EXCLUDE,
                                description="Ignore local virtualenv.",
                                is_enabled=False,
                            ),
                        ),
                    ),
                ),
                use_gitignore_rules=True,
            )
        )
    )

    reloaded_state = service.load_settings()

    assert reloaded_state.app_settings.sync_scope_settings.use_gitignore_rules is True
    assert (
        reloaded_state.app_settings.sync_scope_settings.global_rules[0].relative_path
        == ".git"
    )
    assert (
        reloaded_state.app_settings.sync_scope_settings.framework_rule_sets[
            0
        ].framework_type
        == "django"
    )
    assert (
        reloaded_state.app_settings.sync_scope_settings.framework_rule_sets[0]
        .rules[0]
        .is_enabled
        is False
    )


def test_load_settings_rejects_invalid_toml_values(tmp_path: Path) -> None:
    """Verify load settings rejects invalid toml values.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(
        '[app]\nwindow_width = 0\nlast_opened_screen = "dashboard"\n',
        encoding="utf-8",
    )
    service = TomlSettingsService(settings_path)

    with pytest.raises(
        ControlledServiceError,
        match=r"Window dimensions must be positive integers\.",
    ):
        service.load_settings()


def test_load_settings_rejects_invalid_sync_progress_log_limit(tmp_path: Path) -> None:
    """Verify load settings rejects invalid sync progress log limit.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(
        '[app]\nlast_opened_screen = "dashboard"\nsync_progress_log_limit = 0\n',
        encoding="utf-8",
    )
    service = TomlSettingsService(settings_path)

    with pytest.raises(
        ControlledServiceError,
        match=r"Sync progress log limit must be a positive integer\.",
    ):
        service.load_settings()


def test_load_settings_rejects_invalid_translation_defaults(tmp_path: Path) -> None:
    """Verify load settings rejects invalid translation defaults.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            "[translation]\n"
            'default_project_locale = "asad@"\n'
        ),
        encoding="utf-8",
    )
    service = TomlSettingsService(settings_path)

    with pytest.raises(
        ControlledServiceError,
        match=(
            r"Default project locale must be a valid locale or a comma-separated "
            r"list of valid locales\. Invalid values: asad@\."
        ),
    ):
        service.load_settings()


@pytest.mark.parametrize(
    ("document", "expected_message"),
    [
        (
            'translation = 3\n[app]\nlast_opened_screen = "dashboard"\n',
            r"The \[translation\] settings section must be a TOML table\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            "[translation]\ndefault_project_locale = 3\n",
            r"The translation setting 'default_project_locale' must be a string\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_compile_mo = "yes"\n',
            r"The translation setting 'default_compile_mo' must be a boolean\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_use_external_translator = "yes"\n',
            (
                r"The translation setting 'default_use_external_translator' "
                r"must be a boolean\."
            ),
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_use_translation_cache = "yes"\n',
            (
                r"The translation setting 'default_use_translation_cache' "
                r"must be a boolean\."
            ),
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_only_fuzzy = "yes"\n',
            r"The translation setting 'default_only_fuzzy' must be a boolean\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            "[translation]\ntranslation_cache_path = 3\n",
            r"The translation setting 'translation_cache_path' must be a string\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_dry_run = "yes"\n',
            r"The translation setting 'default_dry_run' must be a boolean\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_stats_only = "yes"\n',
            r"The translation setting 'default_stats_only' must be a boolean\.",
        ),
        (
            '[app]\nlast_opened_screen = "dashboard"\n'
            '[translation]\ndefault_report_inconsistencies = "yes"\n',
            (
                r"The translation setting "
                r"'default_report_inconsistencies' must be a boolean\."
            ),
        ),
    ],
)
def test_load_settings_rejects_invalid_translation_section_shapes(
    tmp_path: Path,
    document: str,
    expected_message: str,
) -> None:
    """Verify load settings rejects invalid translation section shapes.

    Args:
        tmp_path:
            Value supplied to this callable.
        document:
            Value supplied to this callable.
        expected_message:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(document, encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(ControlledServiceError, match=expected_message):
        service.load_settings()


def test_save_settings_normalizes_default_project_locale_spacing(
    tmp_path: Path,
) -> None:
    """Verify save settings normalizes default project locale spacing.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(
        AppSettingsViewModel(default_project_locale="es_ES, es_AR")
    )

    assert saved_state.app_settings.default_project_locale == "es_ES,es_AR"
    assert 'default_project_locale = "es_ES,es_AR"' in settings_path.read_text(
        encoding="utf-8"
    )


def test_save_settings_persists_default_compile_mo(tmp_path: Path) -> None:
    """Verify save settings persists default compile mo.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(AppSettingsViewModel(default_compile_mo=False))

    assert saved_state.app_settings.default_compile_mo is False
    assert "default_compile_mo = false" in settings_path.read_text(encoding="utf-8")


def test_save_settings_persists_default_use_external_translator(tmp_path: Path) -> None:
    """Verify save settings persists default use external translator.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(
        AppSettingsViewModel(default_use_external_translator=False)
    )

    assert saved_state.app_settings.default_use_external_translator is False
    assert "default_use_external_translator = false" in settings_path.read_text(
        encoding="utf-8"
    )


def test_save_settings_persists_default_translation_preview_flags(
    tmp_path: Path,
) -> None:
    """Verify save settings persists default translation preview flags.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(
        AppSettingsViewModel(
            default_dry_run=True,
            default_stats_only=True,
            default_report_inconsistencies=True,
        )
    )

    assert saved_state.app_settings.default_dry_run is True
    assert saved_state.app_settings.default_stats_only is True
    assert saved_state.app_settings.default_report_inconsistencies is True
    saved_text = settings_path.read_text(encoding="utf-8")
    assert "default_dry_run = true" in saved_text
    assert "default_stats_only = true" in saved_text
    assert "default_report_inconsistencies = true" in saved_text


def test_save_settings_rejects_invalid_database_configuration(tmp_path: Path) -> None:
    """Verify save settings rejects invalid database configuration.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)

    with pytest.raises(
        ControlledServiceError,
        match=r"Database filename must not be empty\.",
    ):
        service.save_settings(AppSettingsViewModel(database_filename=""))


@pytest.mark.parametrize(
    ("document", "expected_message"),
    [
        (
            "[sync_scope]\nuse_gitignore_rules = true\nglobal_rules = 3\n",
            r"The sync_scope\.global_rules setting must be an array of TOML tables\.",
        ),
        (
            "[sync_scope]\nframework_rules = 3\n",
            (
                r"The sync_scope\.framework_rules setting must be an array "
                r"of TOML tables\."
            ),
        ),
        (
            "[sync_scope]\n[[sync_scope.global_rules]]\n"
            'relative_path = ".git"\nfilter_type = "broken"\nbehavior = "exclude"\n',
            r"Unsupported sync filter type in sync_scope\.global_rules\[0\]: broken",
        ),
        (
            "[sync_scope]\n[[sync_scope.global_rules]]\n"
            'relative_path = ".git"\nfilter_type = "directory"\nbehavior = "broken"\n',
            r"Unsupported sync rule behavior in sync_scope\.global_rules\[0\]: broken",
        ),
        (
            "[sync_scope]\n[[sync_scope.framework_rules]]\n"
            'framework_type = ""\nrelative_path = ".venv"\n'
            'filter_type = "directory"\nbehavior = "exclude"\n',
            r"Framework sync rules require a non-empty framework_type\.",
        ),
        (
            "[sync_scope]\n[[sync_scope.global_rules]]\n"
            'relative_path = ""\nfilter_type = "directory"\nbehavior = "exclude"\n',
            r"Global sync rule requires a non-empty relative path\.",
        ),
    ],
)
def test_load_settings_rejects_invalid_sync_scope_values(
    tmp_path: Path,
    document: str,
    expected_message: str,
) -> None:
    """Verify load settings rejects invalid sync scope values.

    Args:
        tmp_path:
            Value supplied to this callable.
        document:
            Value supplied to this callable.
        expected_message:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(document, encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(ControlledServiceError, match=expected_message):
        service.load_settings()


@pytest.mark.parametrize(
    ("document", "expected_message"),
    [
        (
            'sync_scope = 3\n[app]\nlast_opened_screen = "dashboard"\n',
            r"The \[sync_scope\] settings section must be a TOML table\.",
        ),
        (
            "[sync_scope]\nglobal_rules = [3]\n",
            r"The sync_scope\.global_rules\[0\] setting must be a TOML table\.",
        ),
        (
            "[sync_scope]\nframework_rules = [3]\n",
            r"The sync_scope\.framework_rules\[0\] setting must be a TOML table\.",
        ),
    ],
)
def test_load_settings_rejects_invalid_sync_scope_section_shapes(
    tmp_path: Path,
    document: str,
    expected_message: str,
) -> None:
    """Verify load settings rejects invalid sync scope section shapes.

    Args:
        tmp_path:
            Value supplied to this callable.
        document:
            Value supplied to this callable.
        expected_message:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(document, encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(ControlledServiceError, match=expected_message):
        service.load_settings()


def test_save_settings_normalizes_sync_rule_descriptions_and_paths(
    tmp_path: Path,
) -> None:
    """Verify save settings normalizes sync rule descriptions and paths.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(
        AppSettingsViewModel(
            sync_scope_settings=AdapterSyncScopeSettings(
                global_rules=(
                    ConfiguredSyncRule(
                        relative_path=" /.git/ ",
                        filter_type=SyncFilterType.DIRECTORY,
                        behavior=SyncRuleBehavior.EXCLUDE,
                        description="",
                        is_enabled=True,
                    ),
                ),
                framework_rule_sets=(
                    FrameworkSyncRuleSet(
                        framework_type=" Django ",
                        rules=(
                            ConfiguredSyncRule(
                                relative_path=" /.venv/ ",
                                filter_type=SyncFilterType.DIRECTORY,
                                behavior=SyncRuleBehavior.EXCLUDE,
                                description="",
                                is_enabled=True,
                            ),
                        ),
                    ),
                ),
                use_gitignore_rules=False,
            )
        )
    )

    assert (
        saved_state.app_settings.sync_scope_settings.global_rules[0].relative_path
        == ".git"
    )
    assert (
        saved_state.app_settings.sync_scope_settings.global_rules[0].description
        == ".git"
    )
    assert (
        saved_state.app_settings.sync_scope_settings.framework_rule_sets[
            0
        ].framework_type
        == "django"
    )


def test_reset_settings_restores_defaults_and_persists_them(tmp_path: Path) -> None:
    """Verify reset settings restores defaults and persists them.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)
    service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="settings",
            developer_mode=True,
            ui_language="es",
        )
    )

    reset_state = service.reset_settings()

    assert reset_state.status == "defaults-restored"
    assert reset_state.app_settings.theme_mode == "system"
    assert reset_state.app_settings.last_opened_screen == "dashboard"
    assert service.load_settings().app_settings.ui_language == "en"


def test_build_default_settings_service_uses_explicit_config_dir(
    tmp_path: Path,
) -> None:
    """Verify build default settings service uses explicit config dir.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = build_default_settings_service(config_dir=tmp_path)

    assert isinstance(service, TomlSettingsService)
    assert service.settings_path == tmp_path / SETTINGS_FILENAME


def test_load_settings_uses_defaults_for_empty_toml_document(tmp_path: Path) -> None:
    """Verify load settings uses defaults for empty toml document.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text("", encoding="utf-8")
    service = TomlSettingsService(settings_path)

    settings_state = service.load_settings()

    assert settings_state.app_settings.window_width == 1280
    assert settings_state.app_settings.ui_language == "en"


def test_load_settings_uses_defaults_when_app_table_is_missing(tmp_path: Path) -> None:
    """Verify load settings uses defaults when app table is missing.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text("[meta]\nschema_version = 1\n", encoding="utf-8")
    service = TomlSettingsService(settings_path)

    settings_state = service.load_settings()

    assert settings_state.app_settings.theme_mode == "system"


def test_load_settings_accepts_partial_app_table_and_fills_defaults(
    tmp_path: Path,
) -> None:
    """Verify load settings accepts partial app table and fills defaults.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text('[app]\ntheme_mode = "dark"\n', encoding="utf-8")
    service = TomlSettingsService(settings_path)

    settings_state = service.load_settings()

    assert settings_state.app_settings.theme_mode == "dark"
    assert settings_state.app_settings.window_width == 1280
    assert settings_state.app_settings.last_opened_screen == "dashboard"


def test_load_settings_rejects_invalid_toml_syntax(tmp_path: Path) -> None:
    """Verify load settings rejects invalid toml syntax.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text("[app\n", encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(
        ControlledServiceError, match=r"App settings contain invalid TOML"
    ):
        service.load_settings()


@pytest.mark.parametrize(
    ("document", "expected_message"),
    [
        ("app = 3\n", r"The \[app\] settings section must be a TOML table\."),
        ("[app]\ntheme_mode = 3\n", r"The app setting 'theme_mode' must be a string\."),
        (
            '[app]\nwindow_width = "wide"\n',
            r"The app setting 'window_width' must be an integer\.",
        ),
        (
            '[app]\nremember_last_screen = "yes"\n',
            r"The app setting 'remember_last_screen' must be a boolean\.",
        ),
        ('[app]\ntheme_mode = "neon"\n', r"Unsupported theme mode: neon"),
        ('[app]\nui_language = "fr"\n', r"Unsupported UI language: fr"),
        (
            '[app]\nlast_opened_screen = "sync-preview"\n',
            r"Unsupported last opened screen: sync-preview",
        ),
    ],
)
def test_load_settings_rejects_invalid_values(
    tmp_path: Path,
    document: str,
    expected_message: str,
) -> None:
    """Verify load settings rejects invalid values.

    Args:
        tmp_path:
            Value supplied to this callable.
        document:
            Value supplied to this callable.
        expected_message:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(document, encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(ControlledServiceError, match=expected_message):
        service.load_settings()


def test_load_settings_wraps_os_errors_from_reading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify load settings wraps os errors from reading.

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
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text('[app]\ntheme_mode = "dark"\n', encoding="utf-8")
    service = TomlSettingsService(settings_path)

    def fail_read_text(_self: Path, *, encoding: str) -> str:
        """Handle fail read text.

        Args:
            _self:
                Value supplied to this callable.
            encoding:
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

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    with pytest.raises(
        ControlledServiceError, match=r"App settings could not be loaded from"
    ):
        service.load_settings()


def test_save_settings_wraps_os_errors_from_writing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify save settings wraps os errors from writing.

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
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)

    def fail_write_text(_self: Path, _content: str, *, encoding: str) -> int:
        """Handle fail write text.

        Args:
            _self:
                Value supplied to this callable.
            _content:
                Value supplied to this callable.
            encoding:
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

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(
        ControlledServiceError, match=r"App settings could not be saved to"
    ):
        service.save_settings(_custom_settings())


def test_resolve_user_config_dir_prefers_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve user config dir prefers env override.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.setenv(settings_module.CONFIG_DIR_ENV_VAR, "~/custom-config")

    assert resolve_user_config_dir() == Path("~/custom-config").expanduser()


def test_resolve_windows_config_dir_uses_appdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve windows config dir uses appdata.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.setenv("APPDATA", "/tmp/appdata")

    assert _resolve_windows_config_dir() == Path(
        "/tmp/appdata/polyglot-site-translator"
    )


def test_resolve_windows_config_dir_uses_fallback_when_appdata_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve windows config dir uses fallback when appdata is missing.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.Path, "home", lambda: Path("/home/tester"))

    assert _resolve_windows_config_dir() == Path(
        "/home/tester/AppData/Roaming/polyglot-site-translator"
    )


def test_resolve_user_config_dir_uses_darwin_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve user config dir uses darwin location.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.delenv(settings_module.CONFIG_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.os, "name", "posix", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.sys, "platform", "darwin", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.Path, "home", lambda: Path("/Users/tester"))

    assert resolve_user_config_dir() == Path(
        "/Users/tester/Library/Application Support/polyglot-site-translator"
    )


def test_resolve_user_config_dir_uses_windows_and_posix_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve user config dir uses windows and posix branches.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.delenv(settings_module.CONFIG_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        settings_module,
        "_resolve_windows_config_dir",
        lambda: Path("/windows/config"),
    )

    assert resolve_user_config_dir() == Path("/windows/config")

    monkeypatch.setattr(SETTINGS_MODULE.os, "name", "posix", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.sys, "platform", "linux", raising=False)
    monkeypatch.setattr(
        settings_module,
        "_resolve_posix_config_dir",
        lambda: Path("/posix/config"),
    )

    assert resolve_user_config_dir() == Path("/posix/config")


def test_resolve_user_config_dir_uses_xdg_config_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve user config dir uses xdg config home.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg")

    assert _resolve_posix_config_dir() == Path("/tmp/xdg/polyglot-site-translator")


def test_resolve_posix_config_dir_uses_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve posix config dir uses fallback.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.Path, "home", lambda: Path("/home/tester"))

    assert _resolve_posix_config_dir() == Path(
        "/home/tester/.config/polyglot-site-translator"
    )


def test_translation_helpers_reject_non_table_sections_directly() -> None:
    """Verify translation helpers reject non table sections directly.

    Returns:
        value:
            Structured value returned by this callable.
    """
    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_default_compile_mo({"translation": 3}, True)

    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_default_use_external_translator(
            {"translation": 3}, True
        )

    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_default_dry_run({"translation": 3}, True)

    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_default_use_translation_cache(
            {"translation": 3},
            True,
        )

    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_cache_path({"translation": 3}, "/tmp/cache")

    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_default_stats_only({"translation": 3}, False)

    with pytest.raises(
        ControlledServiceError,
        match=r"The \[translation\] settings section must be a TOML table\.",
    ):
        SETTINGS_MODULE._read_translation_default_report_inconsistencies(
            {"translation": 3},
            False,
        )


def test_normalize_translation_cache_path_resolves_relative_paths() -> None:
    """Verify normalize translation cache path resolves relative paths.

    Returns:
        value:
            Structured value returned by this callable.
    """
    normalized = SETTINGS_MODULE._normalize_translation_cache_path(
        "cache/translations",
        default_directory=Path("/tmp/app-config"),
    )

    assert normalized == "/tmp/app-config/cache/translations"


def test_validate_sync_scope_settings_rejects_blank_framework_types_directly() -> None:
    """Verify validate sync scope settings rejects blank framework types directly.

    Returns:
        value:
            Structured value returned by this callable.
    """
    with pytest.raises(
        ControlledServiceError,
        match=r"Framework sync rules require a non-empty framework type\.",
    ):
        SETTINGS_MODULE._validate_sync_scope_settings(
            AdapterSyncScopeSettings(
                framework_rule_sets=(
                    FrameworkSyncRuleSet(
                        framework_type="   ",
                        rules=(
                            ConfiguredSyncRule(
                                relative_path=".venv",
                                filter_type=SyncFilterType.DIRECTORY,
                                behavior=SyncRuleBehavior.EXCLUDE,
                                description="Ignore virtualenv.",
                                is_enabled=True,
                            ),
                        ),
                    ),
                )
            )
        )


def _custom_settings() -> AppSettingsViewModel:
    """Handle custom settings.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return AppSettingsViewModel(
        theme_mode="dark",
        window_width=1440,
        window_height=900,
        remember_last_screen=True,
        last_opened_screen="settings",
        developer_mode=True,
        ui_language="es",
    )
