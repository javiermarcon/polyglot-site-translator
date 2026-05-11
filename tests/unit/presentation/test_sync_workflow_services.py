"""Unit tests for presentation sync workflow adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionTestResult,
)
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryNotFoundError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteProject,
    SiteRegistrationInput,
)
from polyglot_site_translator.domain.sync.models import (
    SyncDirection,
    SyncError,
    SyncProgressEvent,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationWorkflowService,
)


@dataclass
class _ServiceStub:
    """Test helper for ServiceStub.

    Attributes:
        site:
            Documented attribute exposed by this type.
        missing:
            Documented attribute exposed by this type.
    """

    site: RegisteredSite
    missing: bool = False

    def get_site(self, site_id: str) -> RegisteredSite:
        """Handle get site.

        Args:
            self:
                Value supplied to this callable.
            site_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            SiteRegistryNotFoundError:
                Raised when this callable hits the corresponding error path.
        """
        if self.missing:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return self.site

    def detect_framework(self, project_path: str) -> FrameworkDetectionResult:
        """Handle detect framework.

        Args:
            self:
                Value supplied to this callable.
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return FrameworkDetectionResult.unmatched(
            project_path=project_path,
            warnings=["Framework detection is not used in this sync workflow test."],
        )

    @staticmethod
    def test_remote_connection(
        registration: SiteRegistrationInput,
    ) -> RemoteConnectionTestResult:
        """Verify remote connection.

        Args:
            registration:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return RemoteConnectionTestResult(
            success=True,
            connection_type=registration.remote_connection.connection_type
            if registration.remote_connection is not None
            else "none",
            host=registration.remote_connection.host
            if registration.remote_connection is not None
            else "",
            port=registration.remote_connection.port
            if registration.remote_connection is not None
            else 0,
            message="Connected successfully.",
            error_code=None,
        )


@dataclass
class _ProjectSyncStub:
    """Test helper for ProjectSyncStub.

    Attributes:
        result:
            Documented attribute exposed by this type.
    """

    result: SyncResult

    def sync_remote_to_local(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        """Handle sync remote to local.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.result

    def sync_local_to_remote(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        """Handle sync local to remote.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.result


def test_sync_workflow_service_maps_successful_sync_results() -> None:
    """Verify sync workflow service maps successful sync results.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify sync workflow service maps empty remote results.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify sync workflow service maps controlled failures.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def test_sync_workflow_service_uses_context_when_failure_has_no_error() -> None:
    """Verify sync workflow service uses context when failure has no error.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
                error=None,
            )
        ),
    )

    state = workflow.start_sync("site-123")

    assert state.status == "failed"
    assert state.error_code == "sync_failed"
    assert state.summary == (
        "Remote sync failed for project 'site-123' using sftp into "
        "'/workspace/site', but no detailed sync error was provided."
    )


def test_sync_workflow_service_wraps_missing_site_errors() -> None:
    """Verify sync workflow service wraps missing site errors.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def test_sync_workflow_service_maps_successful_local_to_remote_sync_results() -> None:
    """Verify sync workflow service maps successful local to remote sync results.

    Returns:
        value:
            Structured value returned by this callable.
    """
    workflow = SiteRegistryPresentationWorkflowService(
        service=_ServiceStub(site=_build_site()),
        project_sync_service=_ProjectSyncStub(
            result=SyncResult(
                direction=SyncDirection.LOCAL_TO_REMOTE,
                success=True,
                project_id="site-123",
                connection_type="sftp",
                local_path="/workspace/site",
                summary=SyncSummary(
                    files_discovered=2,
                    files_downloaded=0,
                    directories_created=1,
                    bytes_downloaded=0,
                    files_uploaded=2,
                    bytes_uploaded=64,
                ),
                error=None,
            )
        ),
    )

    state = workflow.start_sync_to_remote("site-123")

    assert state.status == "completed"
    assert state.files_synced == 2
    assert state.error_code is None
    assert (
        state.summary
        == "Uploaded 2 files from /workspace/site into the remote workspace."
    )


def _build_site() -> RegisteredSite:
    """Handle build site.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
