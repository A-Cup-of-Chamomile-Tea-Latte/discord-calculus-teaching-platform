from __future__ import annotations

import asyncio

import pytest

from bots.common.errors import LifecycleError
from bots.common.lifecycle import LifecycleManager
from bots.common.models import HealthStatus
from bots.common.testing import FakeLifecycleComponent


def test_lifecycle_starts_in_order_and_stops_in_reverse_order() -> None:
    async def scenario() -> tuple[list[str], HealthStatus]:
        events: list[str] = []
        manager = LifecycleManager(
            (
                FakeLifecycleComponent("repository", events),
                FakeLifecycleComponent("discord_fixture", events),
            )
        )
        await manager.start()
        assert manager.status is HealthStatus.READY
        manager.request_shutdown()
        await manager.wait_for_shutdown()
        await manager.stop()
        return events, manager.status

    events, status = asyncio.run(scenario())
    assert events == [
        "start:repository",
        "start:discord_fixture",
        "stop:discord_fixture",
        "stop:repository",
    ]
    assert status is HealthStatus.STOPPED


def test_start_failure_cleans_up_already_started_components() -> None:
    async def scenario() -> tuple[list[str], HealthStatus]:
        events: list[str] = []
        manager = LifecycleManager(
            (
                FakeLifecycleComponent("first", events),
                FakeLifecycleComponent("second", events, fail_start=True),
            )
        )
        with pytest.raises(LifecycleError, match="failed during startup"):
            await manager.start()
        return events, manager.status

    events, status = asyncio.run(scenario())
    assert events == ["start:first", "start:second", "stop:first"]
    assert status is HealthStatus.FAILED


def test_duplicate_component_names_are_actionable() -> None:
    events: list[str] = []
    with pytest.raises(LifecycleError, match="names must be unique"):
        LifecycleManager(
            (
                FakeLifecycleComponent("same", events),
                FakeLifecycleComponent("same", events),
            )
        )
