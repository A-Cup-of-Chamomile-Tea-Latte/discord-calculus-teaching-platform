from __future__ import annotations

import pytest

from bots.common.synthetic import (
    FakeInteraction,
    FakeThreadLifecycle,
    SyntheticActor,
    SyntheticActorKind,
    SyntheticEventKind,
    SyntheticThreadState,
    standard_synthetic_actors,
)


def test_standard_fixture_has_student_ta_teacher_and_webhook_like_actor() -> None:
    actors = standard_synthetic_actors()
    assert {actor.kind for actor in actors} == set(SyntheticActorKind)
    assert all(not actor.is_real_discord_account for actor in actors)
    interaction = FakeInteraction(
        "fixture_interaction_dump_001", actors[1], "/dump", (("case", "fixture_case"),)
    )
    assert interaction.actor.kind is SyntheticActorKind.TA


def test_fake_thread_records_read_close_reopen_and_new_activity() -> None:
    student, ta, _, webhook = standard_synthetic_actors()
    lifecycle = FakeThreadLifecycle("fixture_thread_001", student, "2026-07-23T09:00:00+08:00")
    lifecycle.mark_read(ta, "2026-07-23T09:01:00+08:00")
    lifecycle.close(ta, "2026-07-23T09:02:00+08:00")
    lifecycle.add_message(webhook, "2026-07-23T09:03:00+08:00")
    assert lifecycle.state is SyntheticThreadState.OPEN
    assert [event.kind for event in lifecycle.events] == [
        SyntheticEventKind.THREAD_CREATED,
        SyntheticEventKind.READ,
        SyntheticEventKind.CLOSED,
        SyntheticEventKind.REOPENED,
        SyntheticEventKind.MESSAGE_ADDED,
    ]
    assert [event.sequence for event in lifecycle.events] == [1, 2, 3, 4, 5]


def test_synthetic_actor_cannot_be_misrepresented_as_real_account() -> None:
    with pytest.raises(ValueError):
        SyntheticActor(
            "synthetic_student_02",
            SyntheticActorKind.STUDENT,
            "Not Real",
            is_real_discord_account=True,
        )
