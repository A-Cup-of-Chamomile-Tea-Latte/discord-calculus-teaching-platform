"""Narrow protocols that keep reader and writer capabilities separate."""

from __future__ import annotations

from typing import Protocol

from bots.common.models import CaseThreadMapping, CreatedThread, ThreadSnapshot


class CaseThreadMappingRepository(Protocol):
    def get_by_case_id(self, case_id: str) -> CaseThreadMapping | None: ...

    def get_by_thread_id(self, thread_id: str) -> CaseThreadMapping | None: ...

    def upsert(self, mapping: CaseThreadMapping) -> None: ...


class DiscordThreadReader(Protocol):
    async def fetch_thread(
        self,
        *,
        thread_id: str,
        after_message_id: str | None = None,
        limit: int = 100,
    ) -> ThreadSnapshot: ...


class DiscordCourseWriter(Protocol):
    async def create_case_thread(
        self,
        *,
        operation_id: str,
        parent_channel_id: str,
        title: str,
        body: str,
    ) -> CreatedThread: ...

    async def send_message(
        self,
        *,
        operation_id: str,
        thread_id: str,
        body: str,
        parent_message_id: str | None = None,
        suppress_mentions: bool = True,
    ) -> str: ...

    async def set_member_nickname(
        self, *, operation_id: str, member_id: str, nickname: str
    ) -> None: ...

    async def add_member_role(self, *, operation_id: str, member_id: str, role_id: str) -> None: ...

    async def update_thread_status(
        self,
        *,
        operation_id: str,
        thread_id: str,
        status: str,
        tag: str | None,
    ) -> None: ...


class AsyncLifecycleComponent(Protocol):
    @property
    def name(self) -> str: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...
