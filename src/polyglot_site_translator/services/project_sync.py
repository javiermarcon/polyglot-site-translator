"""Application service for project file synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polyglot_site_translator.domain.remote_connections.contracts import (
    RemoteConnectionProvider,
    RemoteConnectionSession,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.models import (
    SyncDirection,
    SyncError,
    SyncProgressCallback,
    SyncProgressEvent,
    SyncProgressStage,
    SyncResult,
    SyncSummary,
)
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

    def _sync_remote_files_incrementally(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        *,
        context: _DownloadContext,
        progress_callback: SyncProgressCallback | None,
    ) -> SyncResult:
        files_discovered = 0
        files_downloaded = 0
        directories_created = context.summary.directories_created
        bytes_downloaded = 0
        try:
            session = context.provider.open_session(context.remote_connection)
        except RemoteConnectionOperationError as error:
            result = self._failure_result(
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
                result = self._failure_result(
                    context=_FailureContext(
                        site=context.site,
                        connection_type=context.connection_type,
                        summary=context.summary,
                    ),
                    error=SyncError(
                        code="remote_listing_failed",
                        message=str(error),
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
                    result = self._failure_result(
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
                            message=str(error),
                        ),
                    )
                    self._emit_failure(progress_callback, result)
                    return result
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
                    result = self._failure_result(
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
                            message=str(error),
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
