import pytest

from ..retry import RetryPolicy


def test_retry_policy_escalates_until_maximum():
    policy = RetryPolicy(max_attempts=4, base_delay_seconds=0.5, max_delay_seconds=2.0)

    delays = [policy.next_delay(i) for i in range(5)]

    assert delays == [0.5, 1.0, 2.0, 2.0, None]
    assert policy.describe()["max_attempts"] == 4


def test_retry_policy_honours_override_limit():
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=0.1, max_delay_seconds=1.0)

    assert policy.next_delay(1, max_attempts_override=2) == 0.2
    assert policy.next_delay(2, max_attempts_override=2) is None


def test_retry_policy_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WORKFLOW_MAX_RETRY_ATTEMPTS", "7")
    try:
        policy = RetryPolicy.from_env()
    finally:
        monkeypatch.delenv("WORKFLOW_MAX_RETRY_ATTEMPTS", raising=False)

    assert policy.max_attempts == 7
