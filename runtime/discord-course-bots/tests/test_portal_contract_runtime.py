from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from discord_course_bots.course_assistant.cogs import (
    normalized_class_module,
    normalized_role_config_key,
)
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
        class_code="01",
        private_support=private,
    )


def test_five_state_lifecycle_and_48_plus_48_scheduler(tmp_path) -> None:
    repo = Repository(tmp_path / "lifecycle.sqlite3")
    _case(repo)
    assert repo.get_case_by_thread(1)["status"] == "OPEN"
    claimed = repo.claim_case(1, 9)
    assert claimed["status"] == "TRACKED"
    assert claimed["teaching_team_replied"] == 0
    assert claimed["last_staff_response_at"] is None

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
    assert canonical_case_status("TEMPORARILY_CLOSED") == "IDLE"


def test_verification_email_outbox_is_durable_idempotent_and_scrubs_secrets(tmp_path) -> None:
    repo = Repository(tmp_path / "email.sqlite3")
    expires = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    delivery_id = repo.enqueue_verification_email(
        challenge_id="email_verification_12345678",
        destination="Student@Example.com",
        verification_code="987654",
        email_kind="INSTITUTIONAL",
        expires_at=expires,
        delivery_id="email_delivery_12345678",
    )
    assert (
        repo.enqueue_verification_email(
            challenge_id="email_verification_12345678",
            destination="student@example.com",
            verification_code="987654",
            email_kind="INSTITUTIONAL",
            expires_at=expires,
            delivery_id=delivery_id,
        )
        == delivery_id
    )
    claim = repo.claim_verification_email("email-worker")
    assert claim is not None
    assert claim.destination == "student@example.com"
    assert claim.verification_code == "987654"
    assert "student@example.com" not in repr(claim)
    assert "987654" not in repr(claim)
    assert repo.complete_verification_email(
        claim.delivery_id, claim.claim_token, "EMAIL_PROVIDER_ACCEPTED"
    )
    row = repo._connection.execute(
        "SELECT destination, verification_code, destination_hash, status "
        "FROM email_delivery_outbox WHERE delivery_id = ?",
        (delivery_id,),
    ).fetchone()
    assert row["destination"] is None
    assert row["verification_code"] is None
    assert len(row["destination_hash"]) == 64
    assert row["status"] == "COMPLETED"


def test_expired_verification_email_is_never_claimed_and_payload_is_scrubbed(tmp_path) -> None:
    repo = Repository(tmp_path / "expired-email.sqlite3")
    now = datetime.now(UTC)
    with repo.transaction() as db:
        db.execute(
            """
            INSERT INTO email_delivery_outbox(
                delivery_id, challenge_id, destination, destination_hash,
                verification_code, email_kind, expires_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
            """,
            (
                "email_delivery_expired1",
                "email_verification_expired1",
                "student@example.com",
                "a" * 64,
                "123456",
                "CONTACT",
                (now - timedelta(minutes=1)).isoformat(),
                (now - timedelta(minutes=2)).isoformat(),
                (now - timedelta(minutes=2)).isoformat(),
            ),
        )
    assert repo.claim_verification_email("email-worker") is None
    row = repo._connection.execute(
        "SELECT status, destination, verification_code, last_error_code FROM email_delivery_outbox"
    ).fetchone()
    assert tuple(row) == ("PERMANENT_FAILURE", None, None, "EMAIL_CODE_EXPIRED")


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
        module_code="M2",
        keyword="積分觀念",
    )
    completed = repo.complete_private_open_request(
        interaction_id="100",
        channel_id=30,
        jump_url="https://discord.example/channels/10/30",
        requester_id=20,
        ai_content_permission=True,
    )
    assert completed["case_number"].endswith("-P")
    case = repo.get_case_by_thread(30)
    assert case["visibility"] == "PRIVATE"
    assert case["status"] == "OPEN"
    assert case["module_code"] == "M2"
    assert case["keyword"] == "積分觀念"
    assert case["canonical_title"].startswith("[M2 | C99][積分觀念]")
    dm_claim = repo.claim_dm_message("dm-worker")
    assert dm_claim is not None
    assert repo.get_dm_message(dm_claim.message_key)["status"] == "CLAIMED"
    assert repo.complete_dm_message(dm_claim.message_key, dm_claim.claim_token)
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
        class_code="01",
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
    renamed, duplicate = repo.submit_join_application(
        applicant_type="STUDENT",
        discord_username="student.renamed",
        identity_email="student@ntu.edu.tw",
        ntu_mail="student@ntu.edu.tw",
        class_code="01",
    )
    assert duplicate is True
    assert renamed["application_id"] == application["application_id"]

    app_id = str(application["application_id"])
    waiting = repo.transition_join_application(
        app_id,
        action="APPROVE",
        actor_id=91,
        reason_code="REVIEW_APPROVED",
    )
    assert waiting["status"] == "WAITING_FOR_DISCORD_MEMBER"
    repo.bind_join_discord_member(app_id, 20)
    nickname = repo.reserve_course_alias(app_id, observed_max=6)
    assert nickname == "Student_01007"
    assert repo.reserve_course_alias(app_id, observed_max=99) == nickname
    repo.transition_join_application(
        app_id,
        action="APPROVE",
        actor_id=91,
        reason_code="REVIEW_APPROVED",
        desired_role_ids=(100, 101),
        desired_nickname=nickname,
    )
    role_claim = repo.claim_course_role_job("worker")
    assert role_claim is not None
    assert repo.complete_course_role_job(role_claim.job_id, role_claim.claim_token, nickname)
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


def test_join_application_matches_portal_validation_contract(tmp_path) -> None:
    repo = Repository(tmp_path / "join-validation.sqlite3")
    application, duplicate = repo.submit_join_application(
        applicant_type="STUDENT",
        discord_username="student.name",
        identity_email="student@ntu.edu.tw",
        ntu_mail="student@ntu.edu.tw",
        contact_email="student.contact@gmail.com",
        class_code="01",
    )
    assert duplicate is False
    assert application["class_code"] == "01"

    for email, contact in (
        ("student@example.com", None),
        ("student@ntu.edu.tw", "student@example.com"),
    ):
        try:
            repo.submit_join_application(
                applicant_type="STUDENT",
                discord_username="another.student",
                identity_email=email,
                ntu_mail=email,
                contact_email=contact,
                class_code="02",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Portal-invalid student email must be rejected by Bot backend")


def test_student_message_reopens_closed_case_and_queues_discord_restore(tmp_path) -> None:
    repo = Repository(tmp_path / "message-reopen.sqlite3")
    _case(repo)
    assert repo.claim_case(1, 9) is not None
    assert repo.close_case(1) is not None
    reopened = repo.record_case_activity(1, actor_id=3, is_staff=False)
    assert reopened is not None
    assert reopened["status"] == "TRACKED"
    assert reopened["reopen_count"] == 1
    transitions = repo._connection.execute(
        "SELECT transition FROM discord_lifecycle_jobs ORDER BY created_at, rowid"
    ).fetchall()
    assert [str(row["transition"]) for row in transitions] == ["CLOSE", "REOPEN"]


def test_course_manager_configuration_keys_are_allowlisted() -> None:
    assert normalized_role_config_key("class_role_01") == "class_role_01"
    assert normalized_role_config_key(" COURSE_ROLE_ID ") == "course_role_id"
    assert normalized_class_module("C09", "m2") == ("09", "M2")
    with pytest.raises(ValueError):
        normalized_role_config_key("administrator_role_id")
    with pytest.raises(ValueError):
        normalized_role_config_key("class_role_99")
    with pytest.raises(ValueError):
        normalized_class_module("01", "M9")


def test_dm_outbox_claim_is_token_owned_and_retryable(tmp_path) -> None:
    repo = Repository(tmp_path / "dm.sqlite3")
    _case(repo)
    case = repo.get_case_by_thread(1)
    repo.enqueue_case_dm(
        case_id=str(case["case_id"]),
        recipient_id=3,
        case_number=str(case["case_number"]),
        jump_url="https://discord.example/case",
    )
    claim = repo.claim_dm_message("worker")
    assert claim is not None
    assert not repo.complete_dm_message(claim.message_key, "stale-token")
    assert repo.fail_dm_message(
        claim.message_key,
        claim.claim_token,
        error_code="DM_SEND_RETRY",
        retryable=True,
    )
    row = repo.get_dm_message(claim.message_key)
    assert row["status"] == "RETRYABLE_FAILURE"
    assert row["next_attempt_at"] is not None


def test_role_job_can_be_requeued_after_permanent_failure(tmp_path) -> None:
    repo = Repository(tmp_path / "role-retry.sqlite3")
    application, _ = repo.submit_join_application(
        applicant_type="STUDENT",
        discord_username="retry.student",
        identity_email="retry@ntu.edu.tw",
        class_code="01",
    )
    application_id = str(application["application_id"])
    repo.bind_join_discord_member(application_id, 20)
    repo.transition_join_application(
        application_id,
        action="APPROVE",
        actor_id=91,
        reason_code="FIRST_APPROVAL",
        desired_role_ids=(100,),
        desired_nickname="Student_01001",
    )
    first = repo.claim_course_role_job("worker")
    assert first is not None
    assert repo.fail_course_role_job(
        first.job_id,
        first.claim_token,
        error_code="DISCORD_FORBIDDEN",
        retryable=False,
    )

    repo.transition_join_application(
        application_id,
        action="APPROVE",
        actor_id=91,
        reason_code="CONFIG_FIXED",
        desired_role_ids=(200,),
        desired_nickname="Student_01001",
    )
    retried = repo.claim_course_role_job("worker")
    assert retried is not None
    job = repo.get_course_role_job(retried.job_id)
    assert job["desired_roles_json"] == "[200]"
