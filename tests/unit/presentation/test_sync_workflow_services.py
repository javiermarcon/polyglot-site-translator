"""Unit tests for presentation sync workflow adapters."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.remote_connections.models import RemoteConnectionConfig
from polyglot_site_translator.domain.site_registry.errors import SiteRegistryNotFoundError
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.domain.sync.models import (
    SyncDirection,
    SyncError,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationWorkflowService,
)


@dataclass
class _ServiceStub:
    site: RegisteredSite
    missing: bool = False

    def get_site(self, site_id: str) -> RegisteredSite:
        if self.missing:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return self.site

    def detect_framework(self, project_path: str) -> FrameworkDetectionResult:
        return FrameworkDetectionResult.unmatched(
            project_path=project_path,
            warnings=["Framework detection is not used in this sync workflow test."],
        )


@dataclass
class _ProjectSyncStub:
    result: SyncResult

    def sync_remote_to_local(self, site: RegisteredSite) -> SyncResult:
        return self.result


def test_sync_workflow_service_maps_successful_sync_results() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=_ServiceStub(site=_build_site()),
        project_sync_service=_ProjectSyncStub(
            result=SyncResult(
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
        ),
    )

    state = workflow.start_sync("site-123")

    assert state.status == "completed"
    assert state.files_synced == 2
    assert state.error_code is None
    assert state.summary == "Downloaded 2 files into /workspace/site."


def test_sync_workflow_service_maps_empty_remote_results() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=_ServiceStub(site=_build_site()),
        project_sync_service=_ProjectSyncStub(
            result=SyncResult(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                success=True,
                project_id="site-123",
                connection_type="sftp",
                local_path="/workspace/site",
                summary=SyncSummary(
                    files_discovered=0,
                    files_downloaded=0,
                    directories_created=1,
                    bytes_downloaded=0,
                ),
                error=None,
            )
        ),
    )

    state = workflow.start_sync("site-123")

    assert state.status == "completed"
    assert state.files_synced == 0
    assert state.summary == "Remote workspace is empty. No files were downloaded."


def test_sync_workflow_service_maps_controlled_failures() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=_ServiceStub(site=_build_site()),
        project_sync_service=_ProjectSyncStub(
            result=SyncResult(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                success=False,
                project_id="site-123",
                connection_type="sftp",
                local_path="/workspace/site",
                summary=SyncSummary(
                    files_discovered=2,
                    files_downloaded=1,
                    directories_created=1,
                    bytes_downloaded=32,
                ),
                error=SyncError(
                    code="download_failed",
                    message="Download failed for /srv/app/locale/es.po.",
                    remote_path="/srv/app/locale/es.po",
                    local_path="/workspace/site/locale/es.po",
                ),
            )
        ),
    )

    state = workflow.start_sync("site-123")

    assert state.status == "failed"
    assert state.files_synced == 1
    assert state.error_code == "download_failed"
    assert state.summary == "Download failed for /srv/app/locale/es.po."


def test_sync_workflow_service_wraps_missing_site_errors() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=_ServiceStub(site=_build_site(), missing=True),
        project_sync_service=_ProjectSyncStub(
            result=SyncResult(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                success=True,
                project_id="site-123",
                connection_type="sftp",
                local_path="/workspace/site",
                summary=SyncSummary(
                    files_discovered=0,
                    files_downloaded=0,
                    directories_created=0,
                    bytes_downloaded=0,
                ),
                error=None,
            )
        ),
    )

    with pytest.raises(ControlledServiceError, match="Unknown site id: site-123"):
        workflow.start_sync("site-123")


def _build_site() -> RegisteredSite:
    return RegisteredSite(
        project=SiteProject(
            id="site-123",
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/site",
            default_locale="en_US",
            is_active=True,
        ),
        remote_connection=RemoteConnectionConfig(
            id="remote-site-123",
            site_project_id="site-123",
            connection_type="sftp",
            host="example.test",
            port=22,
            username="deploy",
            password="secret",
            remote_path="/srv/app",
        ),
    )
