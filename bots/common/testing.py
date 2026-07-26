"""Network-free test doubles shared by future bot packages."""

from __future__ import annotations

from dataclasses import dataclass

from bots.common.errors import ResourceNotFoundError
from bots.common.models import CaseThreadMapping, CreatedThread, ThreadSnapshot


class InMemoryCaseThreadMappingRepository:
    def __init__(self, seed: tuple[CaseThreadMapping, ...] = ()) -> None:
        self._by_case: dict[str, CaseThreadMapping] = {}
        for mapping in seed:
            self.upsert(mapping)

    def get_by_case_id(self, case_id: str) -> CaseThreadMapping | None:
        return self._by_case.get(case_id)

    def get_by_thread_id(self, thread_id: str) -> CaseThreadMapping | None:
        return next(
            (mapping for mapping in self._by_case.values() if mapping.thread_id == thread_id),
            None,
        )

    def upsert(self, mapping: CaseThreadMapping) -> None:
        conflict = self.get_by_thread_id(mapping.thread_id)
        if conflict and conflict.case_id != mapping.case_id:
            raise ValueError("A Discord thread may map to only one case.")
        self._by_case[mapping.case_id] = mapping


@dataclass(frozen=True)
class FakeWriteCall:
    operation: str
    operation_id: str
    target_id: str
    body: str | None = None
    mentions_suppressed: bool | None = None


@dataclass(frozen=True)
class FakeReadCall:
    thread_id: str
    after_message_id: str | None
    limit: int


class FakeDiscordClient:
    """Combined fixture double; inject only its narrow reader or writer protocol."""

    def __init__(self, snapshots: tuple[ThreadSnapshot, ...] = ()) -> None:
        self._snapshots = {snapshot.thread_id: snapshot for snapshot in snapshots}
        self.read_calls: list[FakeReadCall] = []
        self.write_calls: list[FakeWriteCall] = []
        self._counter = 0

    async def fetch_thread(
        self,
        *,
        thread_id: str,
        after_message_id: str | None = None,
        limit: int = 100,
    ) -> ThreadSnapshot:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.read_calls.append(FakeReadCall(thread_id, after_message_id, limit))
        snapshot = self._snapshots.get(thread_id)
        if snapshot is None:
            raise ResourceNotFoundError("The fixture thread was not found.")
        messages = snapshot.messages
        if after_message_id is not None:
            matching = [
                index
                for index, message in enumerate(messages)
                if message.message_id == after_message_id
            ]
            if not matching:
                raise ResourceNotFoundError("The fixture cursor was not found.")
            messages = messages[matching[0] + 1 :]
        page = messages[:limit]
        next_cursor = page[-1].message_id if len(messages) > len(page) else None
        return ThreadSnapshot(
            thread_id=snapshot.thread_id,
            messages=page,
            next_cursor=next_cursor,
            fetched_at=snapshot.fetched_at,
        )

    async def create_case_thread(
        self,
        *,
        operation_id: str,
        parent_channel_id: str,
        title: str,
        body: str,
    ) -> CreatedThread:
        self._counter += 1
        thread_id = f"fixture_thread_{self._counter:06d}"
        message_id = f"fixture_message_{self._counter:06d}"
        self.write_calls.append(
            FakeWriteCall("create_case_thread", operation_id, parent_channel_id, body)
        )
        return CreatedThread(thread_id, message_id)

    async def send_message(
        self,
        *,
        operation_id: str,
        thread_id: str,
        body: str,
        parent_message_id: str | None = None,
        suppress_mentions: bool = True,
    ) -> str:
        self._counter += 1
        self.write_calls.append(
            FakeWriteCall(
                "send_message",
                operation_id,
                thread_id,
                body,
                mentions_suppressed=suppress_mentions,
            )
        )
        return f"fixture_message_{self._counter:06d}"

    async def set_member_nickname(
        self, *, operation_id: str, member_id: str, nickname: str
    ) -> None:
        self.write_calls.append(
            FakeWriteCall("set_member_nickname", operation_id, member_id, nickname)
        )

    async def add_member_role(self, *, operation_id: str, member_id: str, role_id: str) -> None:
        self.write_calls.append(FakeWriteCall("add_member_role", operation_id, member_id, role_id))

    async def update_thread_status(
        self,
        *,
        operation_id: str,
        thread_id: str,
        status: str,
        tag: str | None,
    ) -> None:
        self.write_calls.append(
            FakeWriteCall("update_thread_status", operation_id, thread_id, f"{status}:{tag or ''}")
        )


class FakeLifecycleComponent:
    def __init__(
        self,
        name: str,
        events: list[str],
        *,
        fail_start: bool = False,
        fail_stop: bool = False,
    ) -> None:
        self._name = name
        self._events = events
        self._fail_start = fail_start
        self._fail_stop = fail_stop

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> None:
        self._events.append(f"start:{self.name}")
        if self._fail_start:
            raise RuntimeError("fixture start failure")

    async def stop(self) -> None:
        self._events.append(f"stop:{self.name}")
        if self._fail_stop:
            raise RuntimeError("fixture stop failure")
