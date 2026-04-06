"""Unit tests — CAPTCHA system."""
import time
import pytest
from app.captcha import CaptchaManager, CaptchaChallenge


class TestCaptchaGenerate:
    def test_returns_challenge(self):
        c = CaptchaManager.generate()
        assert c.id
        assert c.question
        assert "?" in c.question

    def test_unique_ids(self):
        ids = {CaptchaManager.generate().id for _ in range(10)}
        assert len(ids) == 10

    def test_stored_in_challenges(self):
        c = CaptchaManager.generate()
        assert c.id in CaptchaManager.CHALLENGES


class TestCaptchaVerify:
    def test_correct_answer(self):
        c = CaptchaManager.generate()
        # Parse answer from question
        q = c.question
        if " + " in q:
            a, b = q.replace(" = ?", "").split(" + ")
            answer = int(a) + int(b)
        elif " - " in q:
            a, b = q.replace(" = ?", "").split(" - ")
            answer = int(a) - int(b)
        else:
            a, b = q.replace(" = ?", "").split(" × ")
            answer = int(a) * int(b)
        assert CaptchaManager.verify(c.id, str(answer)) is True

    def test_wrong_answer(self):
        c = CaptchaManager.generate()
        assert CaptchaManager.verify(c.id, "999999") is False

    def test_nonexistent_id(self):
        assert CaptchaManager.verify("nonexistent", "42") is False

    def test_one_time_use(self):
        c = CaptchaManager.generate()
        # First verify (wrong answer) still consumes the challenge
        CaptchaManager.verify(c.id, "0")
        assert CaptchaManager.verify(c.id, "0") is False

    def test_expired_challenge(self):
        c = CaptchaManager.generate()
        # Manually expire it
        CaptchaManager.CHALLENGES[c.id].expires_at = time.time() - 1
        assert CaptchaManager.verify(c.id, "0") is False


class TestCaptchaCleanup:
    def test_cleanup_removes_expired(self):
        c = CaptchaManager.generate()
        CaptchaManager.CHALLENGES[c.id].expires_at = time.time() - 1
        CaptchaManager.LAST_CLEANUP = 0  # Force cleanup
        CaptchaManager._cleanup()
        assert c.id not in CaptchaManager.CHALLENGES

    def test_cleanup_skips_if_recent(self):
        c = CaptchaManager.generate()
        CaptchaManager.CHALLENGES[c.id].expires_at = time.time() - 1
        CaptchaManager.LAST_CLEANUP = time.time()  # Recent
        CaptchaManager._cleanup()
        assert c.id in CaptchaManager.CHALLENGES


class TestCaptchaChallengeVerify:
    def test_verify_method_on_instance(self):
        ch = CaptchaChallenge(
            id="test", question="1 + 1 = ?",
            answer_hash="", expires_at=time.time() + 300,
        )
        # Hash won't match but we test the method runs
        assert ch.verify("wrong") is False

    def test_expired_instance(self):
        ch = CaptchaChallenge(
            id="test", question="1 + 1 = ?",
            answer_hash="something", expires_at=time.time() - 1,
        )
        assert ch.verify("anything") is False
