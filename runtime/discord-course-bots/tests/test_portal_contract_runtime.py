from __future__ import annotations

from datetime import UTC, datetime, timedelta

from discord_course_bots.repository import Repository, canonical_case_status


def _case(repo: Repository, *, thread_id: int = 1, private: bool = False) -> str:
    return repo.create_case(
        case_id=f"case-{thread_id}",
        thread_id=thread_id,
        author_id=3,
        module_code="M1",
        keyword="極限",
        ai_content_permission=False,
        canonical_title="[M1] [極限] 問題",
        initial_snapshot={"title": "問題"},
        private_support=private,
    )


def test_five_state_lifecycle_and_48_plus_48_scheduler(tmp_path) -> None:
    repo = Repository(tmp_path / "lifecycle.sqlite3")
    _case(repo)
    assert repo.get_case_by_thread(1)["status"] == "OPEN"
    assert repo.claim_case(1, 9)["status"] == "TRACKED"

    base = datetime.now(UTC) + timedelta(seconds=1)
    repo.record_case_activity(1, actor_id=9, is_staff=True, occurred_at=base)
    assert repo.mark_due_cases_idle(48 * 3600, now=base + timedelta(hours=48, seconds=1))
    assert repo.get_case_by_thread(1)["status"] == "IDLE"
    assert repo.auto_close_due_cases(48 * 3600, now=base + timedelta(hours=96, seconds=2))
    assert repo.get_case_by_thread(1)["status"] == "AUTO_CLOSED"
    reopened = repo.reopen_case(1)
    assert reopened is not None
    assert reopened["status"] == "TRACKED"
    assert reopened["reopen_count"] == 1


def test_legacy_statuses_are_read_through_compatibility_mapping() -> None:
    assert canonical_case_status("WAITING_FOR_STUDENT") == "IDLE"
    assert canonical_case_status("ANSWERED") == "TRACKED"
    assert canonical_case_status("TEMPORARILY_CLOSED") == "CLOSED"


def test_private_request_is_idempotent_rate_limited_and_content_free(tmp_path) -> None:
    repo = Repository(tmp_path / "private.sqlite3")
    now = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    first = repo.begin_private_open_request(
        interaction_id="100",
        guild_id=10,
        requester_id=20,
        ai_content_permission=False,
        now=now,
    )
    replay = repo.begin_private_open_request(
        interaction_id="100",
        guild_id=10,
        requester_id=20,
        ai_content_permission=False,
        now=now,
    )
    assert first["interaction_id"] == replay["interaction_id"]
    assert first["status"] == "PENDING"

    limited = repo.begin_private_open_request(
        interaction_id="101",
        guild_id=10,
        requester_id=20,
        ai_content_permission=False,
        now=now + timedelta(seconds=30),
    )
    assert limited["status"] == "REJECTED"
    assert limited["rejection_code"] == "RATE_2_MINUTES"
    assert "body" not in limited
    assert "attachments" not in limited


def test_private_request_durable_worker_claim_can_retry(tmp_path) -> None:
    repo = Repository(tmp_path / "private-worker.sqlite3")
    repo.begin_private_open_request(
        interaction_id="200",
        guild_id=10,
        requester_id=20,
        ai_content_permission=False,
    )
    claim = repo.claim_private_open_request("worker")
    assert claim is not None
    assert repo.fail_private_open_request(
        claim.interaction_id,
        claim.claim_token,
        error_code="DISCORD_HTTP_ERROR",
        retryable=True,
    )
    row = repo.get_private_open_request("200")
    assert row["status"] == "RETRYABLE_FAILURE"


def test_private_completion_uses_canonical_p_case_and_dm_outbox(tmp_path) -> None:
    repo = Repository(tmp_path / "private-complete.sqlite3")
    repo.begin_private_open_request(
        interaction_id="100",
        guild_id=10,
        requester_id=20,
        ai_content_permission=True,
    )
    completed = repo.complete_private_open_request(
        interaction_id="100",
        channel_id=30,
        jump_url="https://discord.example/channels/10/30",
        module_code="M1",
        requester_id=20,
        ai_content_permission=True,
    )
    assert completed["case_number"].endswith("-P")
    case = repo.get_case_by_thread(30)
    assert case["visibility"] == "PRIVATE"
    assert case["status"] == "OPEN"
    assert len(repo.pending_dm_messages()) == 1
    assert repo.safe_case_projection(str(completed["case_number"]), allow_private=False) is None
    projection = repo.safe_case_projection(str(completed["case_number"]), allow_private=True)
    assert set(projection) == {
        "caseNumber",
        "caseType",
        "status",
        "updatedAt",
        "teachingTeamReplied",
        "discordUrl",
    }


def test_join_dedup_waiting_approval_archive_and_explicit_grants(tmp_path) -> None:
    repo = Repository(tmp_path / "join.sqlite3")
    application, duplicate = repo.submit_join_application(
        applicant_type="STUDENT",
        discord_username="student.name",
        identity_email="student@ntu.edu.tw",
        ntu_mail="student@ntu.edu.tw",
        class_code="C01",
    )
    assert duplicate is False
    repeated, duplicate = repo.submit_join_application(
        applicant_type="STUDENT",
        discord_username="STUDENT.NAME",
        identity_email="STUDENT@NTU.EDU.TW",
        ntu_mail="student@ntu.edu.tw",
        class_code="C01",
    )
    assert duplicate is True
    assert repeated["application_id"] == application["application_id"]

    app_id = str(application["application_id"])
    waiting = repo.transition_join_application(
        app_id,
        action="APPROVE",
        actor_id=91,
        reason_code="REVIEW_APPROVED",
    )
    assert waiting["status"] == "WAITING_FOR_DISCORD_MEMBER"
    repo.bind_join_discord_member(app_id, 20)
    repo.transition_join_application(
        app_id,
        action="APPROVE",
        actor_id=91,
        reason_code="REVIEW_APPROVED",
        desired_role_ids=(100, 101),
        desired_nickname="C01",
    )
    role_claim = repo.claim_course_role_job("worker")
    assert role_claim is not None
    assert repo.complete_course_role_job(app_id, "C01")
    assert repo.get_join_application(app_id)["status"] == "APPROVED"

    archived = repo.archive_join_application(app_id, actor_id=99, reason="例行整理")
    assert archived["status"] == "ARCHIVED"
    restored = repo.restore_join_application(app_id, actor_id=99)
    assert restored["status"] == "APPROVED"

    assert repo.reviewer_level(91) is None
    repo.set_reviewer_grant(91, level="REVIEWER", actor_id=99, active=True)
    assert repo.reviewer_level(91) == "REVIEWER"
    repo.set_reviewer_grant(91, level="REVIEWER", actor_id=99, active=False)
    assert repo.reviewer_level(91) is None
