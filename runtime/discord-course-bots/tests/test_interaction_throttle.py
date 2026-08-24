from discord_course_bots.course_assistant.interaction_throttle import InteractionThrottle


def test_rapid_repeats_are_rejected_before_a_short_abuse_cooldown() -> None:
    now = 100.0
    throttle = InteractionThrottle(clock=lambda: now)
    key = ("case-reopen", 3, 1)

    assert throttle.retry_after(key) is None
    assert throttle.retry_after(key) == 5
    assert throttle.retry_after(key) == 5
    assert throttle.retry_after(key) == 30
    assert throttle.retry_after(key) == 30

    now += 30
    assert throttle.retry_after(key) is None


def test_throttle_keys_do_not_mix_users_actions_or_cases() -> None:
    throttle = InteractionThrottle(clock=lambda: 100.0)

    assert throttle.retry_after(("case-close", 1, 10)) is None
    assert throttle.retry_after(("case-close", 2, 10)) is None
    assert throttle.retry_after(("case-close", 1, 11)) is None
    assert throttle.retry_after(("case-reopen", 1, 10)) is None
