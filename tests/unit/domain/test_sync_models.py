"""Unit tests for sync domain models."""

from __future__ import annotations

from polyglot_site_translator.domain.sync.errors import (
    SyncConfigurationError,
    SyncOperationError,
)
from polyglot_site_translator.domain.sync.models import (
    SyncDirection,
    SyncError,
    SyncResult,
    SyncSummary,
)


def test_sync_direction_exposes_remote_to_local_value() -> None:
    assert SyncDirection.REMOTE_TO_LOCAL.value == "remote_to_local"


def test_sync_result_can_represent_a_successful_sync() -> None:
    result = SyncResult(
        direction=SyncDirection.REMOTE_TO_LOCAL,
        success=True,
        project_id="site-123",
        connection_type="sftp",
        local_path="/workspace/site",
        summary=SyncSummary(
            files_discovered=2,
            files_downloaded=2,
            directories_created=1,
            bytes_downloaded=64,
        ),
        error=None,
    )

    assert result.success is True
    assert result.summary.files_downloaded == 2
    assert result.error is None


def test_sync_result_can_represent_a_controlled_failure() -> None:
    result = SyncResult(
        direction=SyncDirection.REMOTE_TO_LOCAL,
        success=False,
        project_id="site-123",
        connection_type="sftp",
        local_path="/workspace/site",
        summary=SyncSummary(
            files_discovered=3,
            files_downloaded=1,
            directories_created=1,
            bytes_downloaded=32,
        ),
        error=SyncError(
            code="download_failed",
            message="Could not download /srv/app/locale/es.po",
            remote_path="/srv/app/locale/es.po",
            local_path="/workspace/site/locale/es.po",
        ),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "download_failed"


def test_sync_errors_are_typed() -> None:
    assert str(SyncConfigurationError("missing remote")) == "missing remote"
    assert str(SyncOperationError("download failed")) == "download failed"
