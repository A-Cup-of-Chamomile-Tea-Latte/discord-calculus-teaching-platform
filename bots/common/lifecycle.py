"""Async startup/shutdown orchestration with reverse-order cleanup."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from bots.common.errors import LifecycleError
from bots.common.models import HealthStatus
from bots.common.ports import AsyncLifecycleComponent


class LifecycleManager:
    def __init__(self, components: Sequence[AsyncLifecycleComponent]) -> None:
        self._components = tuple(components)
        names = [component.name for component in self._components]
        if len(names) != len(set(names)):
            raise LifecycleError("Lifecycle component names must be unique.")
        self._started: list[AsyncLifecycleComponent] = []
        self._shutdown_requested = asyncio.Event()
        self.status = HealthStatus.STOPPED

    async def start(self) -> None:
        if self.status is not HealthStatus.STOPPED:
            raise LifecycleError("Lifecycle manager can only start from STOPPED.")
        self.status = HealthStatus.STARTING
        try:
            for component in self._components:
                await component.start()
                self._started.append(component)
        except Exception as error:
            self.status = HealthStatus.FAILED
            await self._stop_started()
            raise LifecycleError("A lifecycle component failed during startup.") from error
        self.status = HealthStatus.READY

    def request_shutdown(self) -> None:
        self._shutdown_requested.set()

    async def wait_for_shutdown(self) -> None:
        await self._shutdown_requested.wait()

    async def stop(self) -> None:
        if self.status is HealthStatus.STOPPED:
            return
        self.status = HealthStatus.STOPPING
        errors = await self._stop_started()
        self.status = HealthStatus.FAILED if errors else HealthStatus.STOPPED
        if errors:
            raise LifecycleError("One or more lifecycle components failed to stop.")

    async def _stop_started(self) -> list[Exception]:
        errors: list[Exception] = []
        while self._started:
            component = self._started.pop()
            try:
                await component.stop()
            except Exception as error:  # cleanup must continue for remaining components
                errors.append(error)
        return errors

    async def __aenter__(self) -> LifecycleManager:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.stop()
