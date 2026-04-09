"""Application service for project file synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from polyglot_site_translator.domain.remote_connections.contracts import (
    RemoteConnectionProvider,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncDirection,
    SyncError,
    SyncProgressCallback,
    SyncProgressEvent,
    SyncProgressStage,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.sync_local import LocalSyncWorkspace


@dataclass(frozen=True)
class _FailureContext:
    site: RegisteredSite
    connection_type: str | None
    summary: SyncSummary


@dataclass(frozen=True)
class _DownloadContext:
    site: RegisteredSite
    connection_type: str
    local_root: Path
    remote_connection: RemoteConnectionConfig
    provider: RemoteConnectionProvider
    summary: SyncSummary


class ProjectSyncService:
    """Orchestrate remote-to-local file synchronization for registered projects."""

    def __init__(
        self,
        *,
        registry: RemoteConnectionRegistry,
        local_workspace: LocalSyncWorkspace | None = None,
    ) -> None:
        self._registry = registry
        self._local_workspace = local_workspace or LocalSyncWorkspace()

    def sync_remote_to_local(
        self,
        site: RegisteredSite,
        progress_callback: SyncProgressCallback | None = None,
    ) -> SyncResult:
        """Synchronize the site's configured remote workspace into the local path."""
        summary = SyncSummary(
            files_discovered=0,
            files_downloaded=0,
            directories_created=0,
            bytes_downloaded=0,
        )
        remote_connection = site.remote_connection
        if remote_connection is None:
            result = self._failure_result(
                context=_FailureContext(site=site, connection_type=None, summary=summary),
                error=SyncError(
                    code="missing_remote_connection",
                    message="Remote to local sync requires a configured remote connection.",
                ),
            )
            self._emit_failure(progress_callback, result)
            return result
        local_root = Path(site.local_path)
        prepared_summary, preparation_failure = self._prepare_local_workspace(
            site=site,
            connection_type=remote_connection.connection_type,
            local_root=local_root,
            summary=summary,
            progress_callback=progress_callback,
        )
        if preparation_failure is not None:
            self._emit_failure(progress_callback, preparation_failure)
            return preparation_failure
        provider, provider_failure = self._resolve_provider(
            site=site,
            connection_type=remote_connection.connection_type,
            summary=prepared_summary,
        )
        if provider_failure is not None:
            self._emit_failure(progress_callback, provider_failure)
            return provider_failure
        if provider is None:
            msg = "Remote sync provider resolution unexpectedly returned None."
            raise AssertionError(msg)
        remote_files, listing_failure = self._list_remote_files(
            site=site,
            connection_type=remote_connection.connection_type,
            summary=prepared_summary,
            provider=provider,
            remote_connection=remote_connection,
            progress_callback=progress_callback,
        )
        if listing_failure is not None:
            self._emit_failure(progress_callback, listing_failure)
            return listing_failure
        summary = SyncSummary(
            files_discovered=len(remote_files),
            files_downloaded=0,
            directories_created=prepared_summary.directories_created,
            bytes_downloaded=0,
        )
        self._emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.LISTING_REMOTE,
                message=f"Discovered {len(remote_files)} remote files.",
                files_discovered=len(remote_files),
                files_downloaded=0,
                total_files=len(remote_files),
                bytes_downloaded=0,
            ),
        )
        if not remote_files:
            result = SyncResult(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                success=True,
                project_id=site.id,
                connection_type=remote_connection.connection_type,
                local_path=site.local_path,
                summary=summary,
                error=None,
            )
            self._emit_completion(progress_callback, result)
            return result
        return self._download_remote_files(
            context=_DownloadContext(
                site=site,
                connection_type=remote_connection.connection_type,
                local_root=local_root,
                remote_connection=remote_connection,
                provider=provider,
                summary=summary,
            ),
            remote_files=remote_files,
            progress_callback=progress_callback,
        )

    def _prepare_local_workspace(
        self,
        *,
        site: RegisteredSite,
        connection_type: str,
        local_root: Path,
        summary: SyncSummary,
        progress_callback: SyncProgressCallback | None,
    ) -> tuple[SyncSummary, SyncResult | None]:
        self._emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.PREPARING_LOCAL,
                message=f"Preparing local workspace at {local_root}.",
            ),
        )
        try:
            directories_created = self._local_workspace.ensure_directory(local_root)
        except OSError as error:
            return summary, self._failure_result(
                context=_FailureContext(
                    site=site,
                    connection_type=connection_type,
                    summary=summary,
                ),
                error=SyncError(
                    code="local_workspace_failed",
                    message=str(error),
                    local_path=str(local_root),
                ),
            )
        if directories_created > 0:
            self._emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.PREPARING_LOCAL,
                    message=f"Created local workspace directories under {local_root}.",
                    command_text=f"LOCAL MKDIR {local_root}",
                ),
            )
        return (
            SyncSummary(
                files_discovered=0,
                files_downloaded=0,
                directories_created=directories_created,
                bytes_downloaded=0,
            ),
            None,
        )

    def _resolve_provider(
        self,
        *,
        site: RegisteredSite,
        connection_type: str,
        summary: SyncSummary,
    ) -> tuple[RemoteConnectionProvider | None, SyncResult | None]:
        try:
            return self._registry.get_provider(connection_type), None
        except LookupError as error:
            return None, self._failure_result(
                context=_FailureContext(
                    site=site,
                    connection_type=connection_type,
                    summary=summary,
                ),
                error=SyncError(
                    code="unsupported_connection_type",
                    message=str(error),
                ),
            )

    def _list_remote_files(  # noqa: PLR0913
        self,
        *,
        site: RegisteredSite,
        connection_type: str,
        summary: SyncSummary,
        provider: RemoteConnectionProvider,
        remote_connection: object,
        progress_callback: SyncProgressCallback | None,
    ) -> tuple[list[RemoteSyncFile], SyncResult | None]:
        try:
            remote_files = provider.list_remote_files(
                cast(RemoteConnectionConfig, remote_connection),
                progress_callback=progress_callback,
            )
        except ModuleNotFoundError:
            return [], self._failure_result(
                context=_FailureContext(
                    site=site,
                    connection_type=connection_type,
                    summary=summary,
                ),
                error=SyncError(
                    code="missing_dependency",
                    message=(
                        "The selected remote sync provider requires an unavailable dependency."
                    ),
                ),
            )
        except OSError as error:
            return [], self._failure_result(
                context=_FailureContext(
                    site=site,
                    connection_type=connection_type,
                    summary=summary,
                ),
                error=SyncError(
                    code="remote_listing_failed",
                    message=str(error),
                ),
            )
        return remote_files, None

    def _download_remote_files(
        self,
        *,
        context: _DownloadContext,
        remote_files: list[RemoteSyncFile],
        progress_callback: SyncProgressCallback | None,
    ) -> SyncResult:
        downloaded_files = 0
        downloaded_bytes = 0
        directories_created = context.summary.directories_created
        for remote_file in remote_files:
            local_file_path = context.local_root / Path(remote_file.relative_path)
            try:
                directories_created += self._local_workspace.ensure_directory(
                    local_file_path.parent
                )
                file_bytes = context.provider.download_file(
                    context.remote_connection,
                    remote_file.remote_path,
                    progress_callback=progress_callback,
                )
                self._local_workspace.write_file(local_file_path, file_bytes)
            except ModuleNotFoundError:
                result = self._failure_result(
                    context=_FailureContext(
                        site=context.site,
                        connection_type=context.connection_type,
                        summary=SyncSummary(
                            files_discovered=context.summary.files_discovered,
                            files_downloaded=downloaded_files,
                            directories_created=directories_created,
                            bytes_downloaded=downloaded_bytes,
                        ),
                    ),
                    error=SyncError(
                        code="missing_dependency",
                        message=(
                            "The selected remote sync provider requires an unavailable dependency."
                        ),
                        remote_path=remote_file.remote_path,
                        local_path=str(local_file_path),
                    ),
                )
                self._emit_failure(progress_callback, result)
                return result
            except OSError as error:
                result = self._failure_result(
                    context=_FailureContext(
                        site=context.site,
                        connection_type=context.connection_type,
                        summary=SyncSummary(
                            files_discovered=context.summary.files_discovered,
                            files_downloaded=downloaded_files,
                            directories_created=directories_created,
                            bytes_downloaded=downloaded_bytes,
                        ),
                    ),
                    error=SyncError(
                        code="download_failed",
                        message=str(error),
                        remote_path=remote_file.remote_path,
                        local_path=str(local_file_path),
                    ),
                )
                self._emit_failure(progress_callback, result)
                return result
            downloaded_files += 1
            downloaded_bytes += len(file_bytes)
            self._emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.WRITING_LOCAL_FILE,
                    message=f"Wrote {remote_file.relative_path} into the local workspace.",
                    command_text=f"LOCAL WRITE {local_file_path}",
                    files_discovered=context.summary.files_discovered,
                    files_downloaded=downloaded_files,
                    total_files=context.summary.files_discovered,
                    bytes_downloaded=downloaded_bytes,
                ),
            )
        result = SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=True,
            project_id=context.site.id,
            connection_type=context.connection_type,
            local_path=context.site.local_path,
            summary=SyncSummary(
                files_discovered=context.summary.files_discovered,
                files_downloaded=downloaded_files,
                directories_created=directories_created,
                bytes_downloaded=downloaded_bytes,
            ),
            error=None,
        )
        self._emit_completion(progress_callback, result)
        return result

    def _failure_result(
        self,
        *,
        context: _FailureContext,
        error: SyncError,
    ) -> SyncResult:
        return SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=False,
            project_id=context.site.id,
            connection_type=context.connection_type,
            local_path=context.site.local_path,
            summary=context.summary,
            error=error,
        )

    def _emit_progress(
        self,
        progress_callback: SyncProgressCallback | None,
        event: SyncProgressEvent,
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(event)

    def _emit_completion(
        self,
        progress_callback: SyncProgressCallback | None,
        result: SyncResult,
    ) -> None:
        self._emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.COMPLETED,
                message="Remote sync completed.",
                files_discovered=result.summary.files_discovered,
                files_downloaded=result.summary.files_downloaded,
                total_files=result.summary.files_discovered,
                bytes_downloaded=result.summary.bytes_downloaded,
            ),
        )

    def _emit_failure(
        self,
        progress_callback: SyncProgressCallback | None,
        result: SyncResult,
    ) -> None:
        error = result.error
        if error is None:
            return
        self._emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.FAILED,
                message=error.message,
                files_discovered=result.summary.files_discovered,
                files_downloaded=result.summary.files_downloaded,
                total_files=result.summary.files_discovered,
                bytes_downloaded=result.summary.bytes_downloaded,
            ),
        )
