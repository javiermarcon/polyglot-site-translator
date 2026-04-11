"""Application service for project file synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import posixpath

from polyglot_site_translator.domain.remote_connections.contracts import (
    RemoteConnectionProvider,
    RemoteConnectionSession,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.models import (
    LocalSyncFile,
    SyncDirection,
    SyncError,
    SyncProgressCallback,
    SyncProgressEvent,
    SyncProgressStage,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.domain.sync.scope import ResolvedSyncScope
from polyglot_site_translator.infrastructure.remote_connections.base import (
    RemoteConnectionOperationError,
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


@dataclass(frozen=True)
class _UploadContext:
    site: RegisteredSite
    connection_type: str
    local_root: Path
    remote_connection: RemoteConnectionConfig
    provider: RemoteConnectionProvider
    summary: SyncSummary


class ProjectSyncService:
    """Orchestrate bidirectional file synchronization for registered projects."""

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
        resolved_scope: ResolvedSyncScope | None = None,
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
                direction=SyncDirection.REMOTE_TO_LOCAL,
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
        return self._sync_remote_files_incrementally(
            context=_DownloadContext(
                site=site,
                connection_type=remote_connection.connection_type,
                local_root=local_root,
                remote_connection=remote_connection,
                provider=provider,
                summary=prepared_summary,
            ),
            progress_callback=progress_callback,
            resolved_scope=resolved_scope,
        )

    def sync_local_to_remote(
        self,
        site: RegisteredSite,
        progress_callback: SyncProgressCallback | None = None,
        resolved_scope: ResolvedSyncScope | None = None,
    ) -> SyncResult:
        """Synchronize the site's local workspace into the configured remote path."""
        summary = SyncSummary(
            files_discovered=0,
            files_downloaded=0,
            directories_created=0,
            bytes_downloaded=0,
            files_uploaded=0,
            bytes_uploaded=0,
        )
        remote_connection = site.remote_connection
        if remote_connection is None:
            result = self._failure_result(
                direction=SyncDirection.LOCAL_TO_REMOTE,
                context=_FailureContext(site=site, connection_type=None, summary=summary),
                error=SyncError(
                    code="missing_remote_connection",
                    message="Local to remote sync requires a configured remote connection.",
                ),
            )
            self._emit_failure(progress_callback, result)
            return result
        local_root = Path(site.local_path)
        try:
            local_files = self._list_local_files(
                local_root=local_root,
                progress_callback=progress_callback,
                resolved_scope=resolved_scope,
            )
        except OSError as error:
            result = self._failure_result(
                direction=SyncDirection.LOCAL_TO_REMOTE,
                context=_FailureContext(
                    site=site,
                    connection_type=remote_connection.connection_type,
                    summary=summary,
                ),
                error=SyncError(
                    code="local_workspace_failed",
                    message=_format_local_listing_error(
                        site=site,
                        local_root=local_root,
                        error=error,
                    ),
                    local_path=str(local_root),
                ),
            )
            self._emit_failure(progress_callback, result)
            return result
        provider, provider_failure = self._resolve_provider(
            site=site,
            connection_type=remote_connection.connection_type,
            summary=summary,
            direction=SyncDirection.LOCAL_TO_REMOTE,
        )
        if provider_failure is not None:
            self._emit_failure(progress_callback, provider_failure)
            return provider_failure
        if provider is None:
            msg = "Remote sync provider resolution unexpectedly returned None."
            raise AssertionError(msg)
        return self._sync_local_files_incrementally(
            context=_UploadContext(
                site=site,
                connection_type=remote_connection.connection_type,
                local_root=local_root,
                remote_connection=remote_connection,
                provider=provider,
                summary=summary,
            ),
            local_files=local_files,
            progress_callback=progress_callback,
            resolved_scope=resolved_scope,
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
            message = _format_local_workspace_error(
                site=site,
                local_root=local_root,
                error=error,
            )
            return summary, self._failure_result(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                context=_FailureContext(
                    site=site,
                    connection_type=connection_type,
                    summary=summary,
                ),
                error=SyncError(
                    code="local_workspace_failed",
                    message=message,
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
                files_uploaded=0,
                bytes_uploaded=0,
            ),
            None,
        )

    def _resolve_provider(
        self,
        *,
        site: RegisteredSite,
        connection_type: str,
        summary: SyncSummary,
        direction: SyncDirection = SyncDirection.REMOTE_TO_LOCAL,
    ) -> tuple[RemoteConnectionProvider | None, SyncResult | None]:
        try:
            return self._registry.get_provider(connection_type), None
        except LookupError as error:
            return None, self._failure_result(
                direction=direction,
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

    def _sync_local_files_incrementally(
        self,
        *,
        context: _UploadContext,
        local_files: list[LocalSyncFile],
        progress_callback: SyncProgressCallback | None,
        resolved_scope: ResolvedSyncScope | None,
    ) -> SyncResult:
        files_discovered = 0
        files_uploaded = 0
        directories_created = context.summary.directories_created
        bytes_uploaded = 0
        try:
            session = context.provider.open_session(context.remote_connection)
        except RemoteConnectionOperationError as error:
            result = self._failure_result(
                direction=SyncDirection.LOCAL_TO_REMOTE,
                context=_FailureContext(
                    site=context.site,
                    connection_type=context.connection_type,
                    summary=context.summary,
                ),
                error=SyncError(code=error.error_code, message=str(error)),
            )
            self._emit_failure(progress_callback, result)
            return result
        try:
            for local_file in local_files:
                if not _scope_includes(resolved_scope, local_file.relative_path):
                    continue
                files_discovered += 1
                self._emit_progress(
                    progress_callback,
                    SyncProgressEvent(
                        stage=SyncProgressStage.LISTING_LOCAL,
                        message=f"Discovered local file {local_file.relative_path}.",
                        files_discovered=files_discovered,
                        files_uploaded=files_uploaded,
                        bytes_uploaded=bytes_uploaded,
                    ),
                )
                remote_file_path = _join_remote_sync_path(
                    context.remote_connection.remote_path,
                    local_file.relative_path,
                )
                remote_parent = posixpath.dirname(remote_file_path)
                try:
                    directories_created += session.ensure_remote_directory(
                        remote_parent,
                        progress_callback=progress_callback,
                    )
                except RemoteConnectionOperationError as error:
                    result = self._failure_result(
                        direction=SyncDirection.LOCAL_TO_REMOTE,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=0,
                                directories_created=directories_created,
                                bytes_downloaded=0,
                                files_uploaded=files_uploaded,
                                bytes_uploaded=bytes_uploaded,
                            ),
                        ),
                        error=SyncError(
                            code=error.error_code,
                            message=str(error),
                            remote_path=remote_parent,
                            local_path=str(local_file.local_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                except OSError as error:
                    result = self._failure_result(
                        direction=SyncDirection.LOCAL_TO_REMOTE,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=0,
                                directories_created=directories_created,
                                bytes_downloaded=0,
                                files_uploaded=files_uploaded,
                                bytes_uploaded=bytes_uploaded,
                            ),
                        ),
                        error=SyncError(
                            code="remote_directory_failed",
                            message=(
                                f"Failed to prepare remote directory '{remote_parent}' for "
                                f"local file '{local_file.local_path}'. Cause: "
                                f"{_format_error_cause(error)}"
                            ),
                            remote_path=remote_parent,
                            local_path=str(local_file.local_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                try:
                    file_bytes = self._local_workspace.read_file(local_file.local_path)
                    session.upload_file(
                        remote_file_path,
                        file_bytes,
                        progress_callback=progress_callback,
                    )
                except RemoteConnectionOperationError as error:
                    result = self._failure_result(
                        direction=SyncDirection.LOCAL_TO_REMOTE,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=0,
                                directories_created=directories_created,
                                bytes_downloaded=0,
                                files_uploaded=files_uploaded,
                                bytes_uploaded=bytes_uploaded,
                            ),
                        ),
                        error=SyncError(
                            code=error.error_code,
                            message=str(error),
                            remote_path=remote_file_path,
                            local_path=str(local_file.local_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                except OSError as error:
                    result = self._failure_result(
                        direction=SyncDirection.LOCAL_TO_REMOTE,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=0,
                                directories_created=directories_created,
                                bytes_downloaded=0,
                                files_uploaded=files_uploaded,
                                bytes_uploaded=bytes_uploaded,
                            ),
                        ),
                        error=SyncError(
                            code="upload_failed",
                            message=(
                                f"Failed to upload local file '{local_file.local_path}' into "
                                f"remote path '{remote_file_path}'. Cause: "
                                f"{_format_error_cause(error)}"
                            ),
                            remote_path=remote_file_path,
                            local_path=str(local_file.local_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                files_uploaded += 1
                bytes_uploaded += len(file_bytes)
            result = SyncResult(
                direction=SyncDirection.LOCAL_TO_REMOTE,
                success=True,
                project_id=context.site.id,
                connection_type=context.connection_type,
                local_path=context.site.local_path,
                summary=SyncSummary(
                    files_discovered=files_discovered,
                    files_downloaded=0,
                    directories_created=directories_created,
                    bytes_downloaded=0,
                    files_uploaded=files_uploaded,
                    bytes_uploaded=bytes_uploaded,
                ),
                error=None,
            )
            self._emit_completion(progress_callback, result)
            return result
        finally:
            self._close_remote_session(session, progress_callback)

    def _list_local_files(
        self,
        *,
        local_root: Path,
        progress_callback: SyncProgressCallback | None,
        resolved_scope: ResolvedSyncScope | None,
    ) -> list[LocalSyncFile]:
        self._emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.LISTING_LOCAL,
                message=f"Listing local files under {local_root}.",
                command_text=f"LOCAL LIST {local_root}",
            ),
        )
        return [
            local_file
            for local_file in self._local_workspace.iter_local_files(local_root)
            if _scope_includes(resolved_scope, local_file.relative_path)
        ]

    def _sync_remote_files_incrementally(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        *,
        context: _DownloadContext,
        progress_callback: SyncProgressCallback | None,
        resolved_scope: ResolvedSyncScope | None,
    ) -> SyncResult:
        files_discovered = 0
        files_downloaded = 0
        directories_created = context.summary.directories_created
        bytes_downloaded = 0
        try:
            session = context.provider.open_session(context.remote_connection)
        except RemoteConnectionOperationError as error:
            result = self._failure_result(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                context=_FailureContext(
                    site=context.site,
                    connection_type=context.connection_type,
                    summary=context.summary,
                ),
                error=SyncError(
                    code=error.error_code,
                    message=str(error),
                ),
            )
            self._emit_failure(progress_callback, result)
            return result
        try:
            try:
                remote_files = session.iter_remote_files(progress_callback=progress_callback)
            except RemoteConnectionOperationError as error:
                result = self._failure_result(
                    direction=SyncDirection.REMOTE_TO_LOCAL,
                    context=_FailureContext(
                        site=context.site,
                        connection_type=context.connection_type,
                        summary=context.summary,
                    ),
                    error=SyncError(
                        code=error.error_code,
                        message=str(error),
                    ),
                )
                self._emit_failure(progress_callback, result)
                return result
            except ModuleNotFoundError:
                result = self._failure_result(
                    direction=SyncDirection.REMOTE_TO_LOCAL,
                    context=_FailureContext(
                        site=context.site,
                        connection_type=context.connection_type,
                        summary=context.summary,
                    ),
                    error=SyncError(
                        code="missing_dependency",
                        message=(
                            "The selected remote sync provider requires an unavailable dependency."
                        ),
                    ),
                )
                self._emit_failure(progress_callback, result)
                return result
            except OSError as error:
                message = _format_remote_listing_error(
                    context=context,
                    error=error,
                )
                result = self._failure_result(
                    direction=SyncDirection.REMOTE_TO_LOCAL,
                    context=_FailureContext(
                        site=context.site,
                        connection_type=context.connection_type,
                        summary=context.summary,
                    ),
                    error=SyncError(
                        code="remote_listing_failed",
                        message=message,
                    ),
                )
                self._emit_failure(progress_callback, result)
                return result
            remote_file_iterator = iter(remote_files)
            while True:
                try:
                    remote_file = next(remote_file_iterator)
                except StopIteration:
                    break
                except RemoteConnectionOperationError as error:
                    result = self._failure_result(
                        direction=SyncDirection.REMOTE_TO_LOCAL,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=files_downloaded,
                                directories_created=directories_created,
                                bytes_downloaded=bytes_downloaded,
                            ),
                        ),
                        error=SyncError(
                            code=error.error_code,
                            message=str(error),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                except ModuleNotFoundError:
                    result = self._failure_result(
                        direction=SyncDirection.REMOTE_TO_LOCAL,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=files_downloaded,
                                directories_created=directories_created,
                                bytes_downloaded=bytes_downloaded,
                            ),
                        ),
                        error=SyncError(
                            code="missing_dependency",
                            message=(
                                "The selected remote sync provider requires an unavailable "
                                "dependency."
                            ),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                except OSError as error:
                    message = _format_remote_listing_error(
                        context=context,
                        error=error,
                    )
                    result = self._failure_result(
                        direction=SyncDirection.REMOTE_TO_LOCAL,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=files_downloaded,
                                directories_created=directories_created,
                                bytes_downloaded=bytes_downloaded,
                            ),
                        ),
                        error=SyncError(
                            code="remote_listing_failed",
                            message=message,
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                if not _scope_includes(resolved_scope, remote_file.relative_path):
                    continue
                files_discovered += 1
                self._emit_progress(
                    progress_callback,
                    SyncProgressEvent(
                        stage=SyncProgressStage.LISTING_REMOTE,
                        message=f"Discovered remote file {remote_file.relative_path}.",
                        files_discovered=files_discovered,
                        files_downloaded=files_downloaded,
                        bytes_downloaded=bytes_downloaded,
                    ),
                )
                local_file_path = context.local_root / Path(remote_file.relative_path)
                try:
                    directories_created += self._local_workspace.ensure_directory(
                        local_file_path.parent
                    )
                    file_bytes = session.download_file(
                        remote_file.remote_path,
                        progress_callback=progress_callback,
                    )
                    self._local_workspace.write_file(local_file_path, file_bytes)
                except RemoteConnectionOperationError as error:
                    result = self._failure_result(
                        direction=SyncDirection.REMOTE_TO_LOCAL,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=files_downloaded,
                                directories_created=directories_created,
                                bytes_downloaded=bytes_downloaded,
                            ),
                        ),
                        error=SyncError(
                            code=error.error_code,
                            message=str(error),
                            remote_path=remote_file.remote_path,
                            local_path=str(local_file_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                except ModuleNotFoundError:
                    result = self._failure_result(
                        direction=SyncDirection.REMOTE_TO_LOCAL,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=files_downloaded,
                                directories_created=directories_created,
                                bytes_downloaded=bytes_downloaded,
                            ),
                        ),
                        error=SyncError(
                            code="missing_dependency",
                            message=(
                                "The selected remote sync provider requires an unavailable "
                                "dependency."
                            ),
                            remote_path=remote_file.remote_path,
                            local_path=str(local_file_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                except OSError as error:
                    message = _format_remote_download_error(
                        remote_path=remote_file.remote_path,
                        local_path=local_file_path,
                        error=error,
                    )
                    result = self._failure_result(
                        direction=SyncDirection.REMOTE_TO_LOCAL,
                        context=_FailureContext(
                            site=context.site,
                            connection_type=context.connection_type,
                            summary=SyncSummary(
                                files_discovered=files_discovered,
                                files_downloaded=files_downloaded,
                                directories_created=directories_created,
                                bytes_downloaded=bytes_downloaded,
                            ),
                        ),
                        error=SyncError(
                            code="download_failed",
                            message=message,
                            remote_path=remote_file.remote_path,
                            local_path=str(local_file_path),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
                files_downloaded += 1
                bytes_downloaded += len(file_bytes)
                self._emit_progress(
                    progress_callback,
                    SyncProgressEvent(
                        stage=SyncProgressStage.WRITING_LOCAL_FILE,
                        message=(f"Wrote {remote_file.relative_path} into the local workspace."),
                        command_text=f"LOCAL WRITE {local_file_path}",
                        files_discovered=files_discovered,
                        files_downloaded=files_downloaded,
                        bytes_downloaded=bytes_downloaded,
                    ),
                )
        finally:
            self._close_remote_session(session, progress_callback)
        if files_discovered == 0:
            result = SyncResult(
                direction=SyncDirection.REMOTE_TO_LOCAL,
                success=True,
                project_id=context.site.id,
                connection_type=context.connection_type,
                local_path=context.site.local_path,
                summary=SyncSummary(
                    files_discovered=0,
                    files_downloaded=0,
                    directories_created=directories_created,
                    bytes_downloaded=0,
                ),
                error=None,
            )
            self._emit_completion(progress_callback, result)
            return result
        result = SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=True,
            project_id=context.site.id,
            connection_type=context.connection_type,
            local_path=context.site.local_path,
            summary=SyncSummary(
                files_discovered=files_discovered,
                files_downloaded=files_downloaded,
                directories_created=directories_created,
                bytes_downloaded=bytes_downloaded,
            ),
            error=None,
        )
        self._emit_completion(progress_callback, result)
        return result

    def _close_remote_session(
        self,
        session: RemoteConnectionSession,
        progress_callback: SyncProgressCallback | None,
    ) -> None:
        try:
            session.close(progress_callback=progress_callback)
        except RemoteConnectionOperationError as error:
            self._emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.FAILED,
                    message=f"Remote session close failed: {error}",
                ),
            )
        except OSError as error:
            self._emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.FAILED,
                    message=f"Remote session close failed: {error}",
                ),
            )

    def _failure_result(
        self,
        *,
        direction: SyncDirection,
        context: _FailureContext,
        error: SyncError,
    ) -> SyncResult:
        return SyncResult(
            direction=direction,
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
                message=(
                    "Remote to local sync completed."
                    if result.direction is SyncDirection.REMOTE_TO_LOCAL
                    else "Local to remote sync completed."
                ),
                files_discovered=result.summary.files_discovered,
                files_downloaded=result.summary.files_downloaded,
                files_uploaded=result.summary.files_uploaded,
                total_files=result.summary.files_discovered,
                bytes_downloaded=result.summary.bytes_downloaded,
                bytes_uploaded=result.summary.bytes_uploaded,
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
                files_uploaded=result.summary.files_uploaded,
                total_files=result.summary.files_discovered,
                bytes_downloaded=result.summary.bytes_downloaded,
                bytes_uploaded=result.summary.bytes_uploaded,
            ),
        )


def _format_local_workspace_error(
    *,
    site: RegisteredSite,
    local_root: Path,
    error: OSError,
) -> str:
    return (
        f"Failed to prepare local workspace '{local_root}' for project '{site.name}'. "
        f"Cause: {_format_error_cause(error)}"
    )


def _format_remote_listing_error(
    *,
    context: _DownloadContext,
    error: OSError,
) -> str:
    remote_connection = context.remote_connection
    return (
        f"Failed to list remote files for project '{context.site.name}' from "
        f"{remote_connection.connection_type} {remote_connection.host}:{remote_connection.port} "
        f"at remote path '{remote_connection.remote_path}'. "
        f"Cause: {_format_error_cause(error)}"
    )


def _format_remote_download_error(
    *,
    remote_path: str,
    local_path: Path,
    error: OSError,
) -> str:
    return (
        f"Failed to download remote file '{remote_path}' into local path '{local_path}'. "
        f"Cause: {_format_error_cause(error)}"
    )


def _format_local_listing_error(
    *,
    site: RegisteredSite,
    local_root: Path,
    error: OSError,
) -> str:
    return (
        f"Failed to list local files under '{local_root}' for project '{site.name}'. "
        f"Cause: {_format_error_cause(error)}"
    )


def _join_remote_sync_path(remote_root: str, relative_path: str) -> str:
    normalized_root = posixpath.normpath(remote_root)
    if normalized_root == "/":
        return f"/{relative_path.lstrip('/')}"
    return posixpath.join(normalized_root, relative_path)


def _scope_includes(
    resolved_scope: ResolvedSyncScope | None,
    relative_path: str,
) -> bool:
    if resolved_scope is None:
        return True
    return resolved_scope.includes(relative_path)


def _format_error_cause(error: BaseException) -> str:
    return str(error).strip() or error.__class__.__name__
