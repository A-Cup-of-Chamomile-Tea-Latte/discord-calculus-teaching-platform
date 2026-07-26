"""Offline-only synthetic Discord actors and lifecycle events for tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SyntheticActorKind(StrEnum):
    STUDENT = "STUDENT"
    TA = "TA"
    TEACHER = "TEACHER"
    WEBHOOK = "WEBHOOK"


class SyntheticThreadState(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SyntheticEventKind(StrEnum):
    THREAD_CREATED = "THREAD_CREATED"
    MESSAGE_ADDED = "MESSAGE_ADDED"
    READ = "READ"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


@dataclass(frozen=True)
class SyntheticActor:
    actor_id: str
    kind: SyntheticActorKind
    display_name: str
    is_real_discord_account: bool = False

    def __post_init__(self) -> None:
        if self.is_real_discord_account:
            raise ValueError("synthetic actors cannot represent real Discord accounts")
        if not self.actor_id.startswith("synthetic_"):
            raise ValueError("synthetic actor IDs must use the synthetic_ prefix")


@dataclass(frozen=True)
class FakeInteraction:
    interaction_id: str
    actor: SyntheticActor
    command: str
    options: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.interaction_id.startswith("fixture_interaction_"):
            raise ValueError("fake interaction IDs must be visibly fixture-only")
        if not self.command.startswith("/"):
            raise ValueError("command must start with /")


@dataclass(frozen=True)
class SyntheticThreadEvent:
    sequence: int
    kind: SyntheticEventKind
    actor_id: str
    occurred_at: str


class FakeThreadLifecycle:
    def __init__(self, thread_id: str, creator: SyntheticActor, occurred_at: str) -> None:
        if not thread_id.startswith("fixture_thread_"):
            raise ValueError("fake thread IDs must be visibly fixture-only")
        self.thread_id = thread_id
        self.state = SyntheticThreadState.OPEN
        self.events = [
            SyntheticThreadEvent(
                1, SyntheticEventKind.THREAD_CREATED, creator.actor_id, occurred_at
            )
        ]

    def add_message(self, actor: SyntheticActor, occurred_at: str) -> SyntheticThreadEvent:
        if self.state is SyntheticThreadState.CLOSED:
            self.reopen(actor, occurred_at)
        return self._append(SyntheticEventKind.MESSAGE_ADDED, actor, occurred_at)

    def mark_read(self, actor: SyntheticActor, occurred_at: str) -> SyntheticThreadEvent:
        return self._append(SyntheticEventKind.READ, actor, occurred_at)

    def close(self, actor: SyntheticActor, occurred_at: str) -> SyntheticThreadEvent:
        if self.state is SyntheticThreadState.CLOSED:
            raise ValueError("fixture thread is already closed")
        self.state = SyntheticThreadState.CLOSED
        return self._append(SyntheticEventKind.CLOSED, actor, occurred_at)

    def reopen(self, actor: SyntheticActor, occurred_at: str) -> SyntheticThreadEvent:
        if self.state is SyntheticThreadState.OPEN:
            raise ValueError("fixture thread is already open")
        self.state = SyntheticThreadState.OPEN
        return self._append(SyntheticEventKind.REOPENED, actor, occurred_at)

    def _append(
        self, kind: SyntheticEventKind, actor: SyntheticActor, occurred_at: str
    ) -> SyntheticThreadEvent:
        event = SyntheticThreadEvent(len(self.events) + 1, kind, actor.actor_id, occurred_at)
        self.events.append(event)
        return event


def standard_synthetic_actors() -> tuple[SyntheticActor, ...]:
    return (
        SyntheticActor("synthetic_student_01", SyntheticActorKind.STUDENT, "Fixture Student"),
        SyntheticActor("synthetic_ta_01", SyntheticActorKind.TA, "Fixture TA"),
        SyntheticActor("synthetic_teacher_01", SyntheticActorKind.TEACHER, "Fixture Teacher"),
        SyntheticActor("synthetic_webhook_01", SyntheticActorKind.WEBHOOK, "Fixture Webhook"),
    )
