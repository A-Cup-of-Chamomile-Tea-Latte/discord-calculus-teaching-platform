"""Local/admin command-shaped entrypoint; intentionally not a Discord command tree."""

from __future__ import annotations

from collections.abc import Callable

from bots.archive_reader.models import ExportCommand, ExportHandoff, ManagerContext
from bots.archive_reader.service import ArchiveReaderService
from bots.common.config import ArchiveReaderConfig
from bots.common.errors import LifecycleError, NotConfiguredError
from bots.common.models import HealthInfo, HealthStatus


class ArchiveReaderAdminApp:
    command_names = ("/dump", "/follow")

    def __init__(
        self,
        config: ArchiveReaderConfig,
        service: ArchiveReaderService,
        *,
        now: Callable[[], str],
    ) -> None:
        self._config = config
        self._service = service
        self._now = now
        self.status = HealthStatus.STOPPED

    @property
    def name(self) -> str:
        return "archive_reader_admin_app"

    async def start(self) -> None:
        if self._config.network_enabled:
            raise NotConfiguredError(
                "Live Discord REST startup is intentionally absent from the fixture skeleton."
            )
        self.status = HealthStatus.READY

    async def stop(self) -> None:
        self.status = HealthStatus.STOPPED

    def health(self) -> HealthInfo:
        return self._service.health(self.status, self._now())

    async def dump(self, actor: ManagerContext, command: ExportCommand) -> ExportHandoff:
        self._require_ready()
        return await self._service.dump(actor, command)

    async def follow(self, actor: ManagerContext, command: ExportCommand) -> ExportHandoff:
        self._require_ready()
        return await self._service.follow(actor, command)

    def _require_ready(self) -> None:
        if self.status is not HealthStatus.READY:
            raise LifecycleError("Archive Reader admin app is not ready.")
