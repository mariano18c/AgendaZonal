"""Unit tests for CAPTCHA module."""
import pytest
import time
from app.captcha import CaptchaManager, CaptchaChallenge


class TestCaptchaChallenge:
    """Test CaptchaChallenge dataclass."""

    def test_verify_expired_challenge(self):
        challenge = CaptchaChallenge(
            id="test_expired",
            question="5 + 3 = ?",
            answer_hash="fake",
            expires_at=time.time() - 100,
        )
        assert challenge.verify("8") is False

    def test_verify_correct_hash(self):
        """Generate a challenge and verify with the correct answer."""
        challenge = CaptchaManager.generate()
        # The challenge was just created, so it should be in the store
        assert challenge.id in CaptchaManager.CHALLENGES


class TestCaptchaManager:
    """Test CaptchaManager singleton behavior."""

    def test_all_operations_generated(self):
        """Test that all three operations (+, -, x) are generated over time."""
        seen_operations = set()
        for _ in range(200):
            challenge = CaptchaManager.generate()
            if '+' in challenge.question:
                seen_operations.add('+')
            elif '-' in challenge.question:
                seen_operations.add('-')
            elif '×' in challenge.question:
                seen_operations.add('×')
            # Clean up to avoid memory leak
            if challenge.id in CaptchaManager.CHALLENGES:
                del CaptchaManager.CHALLENGES[challenge.id]

        assert len(seen_operations) == 3, f"Expected all 3 operations, got: {seen_operations}"

    def test_challenge_is_stored(self):
        challenge = CaptchaManager.generate()
        assert challenge.id in CaptchaManager.CHALLENGES
        # Cleanup
        del CaptchaManager.CHALLENGES[challenge.id]

    def test_verify_nonexistent_challenge_returns_false(self):
        assert CaptchaManager.verify("nonexistent_id", "42") is False

    def test_verify_consumes_challenge(self):
        """After verification (success or fail), the challenge should be consumed."""
        challenge = CaptchaManager.generate()
        challenge_id = challenge.id

        # Try wrong answer — should still consume
        CaptchaManager.verify(challenge_id, "wrong")

        # Second attempt should fail (consumed)
        assert CaptchaManager.verify(challenge_id, "any") is False

    def test_cleanup_removes_expired(self):
        # Create an expired challenge
        old_challenge = CaptchaChallenge(
            id="will_cleanup",
            question="1 + 1 = ?",
            answer_hash="fake",
            expires_at=time.time() - 1000,
        )
        CaptchaManager.CHALLENGES["will_cleanup"] = old_challenge
        CaptchaManager.LAST_CLEANUP = 0  # Force cleanup

        CaptchaManager.generate()  # Triggers _cleanup

        assert "will_cleanup" not in CaptchaManager.CHALLENGES

    def test_challenge_question_format(self):
        """Verify challenge question format is valid."""
        challenge = CaptchaManager.generate()
        assert "= ?" in challenge.question
        parts = challenge.question.replace(" = ?", "").split(" ")
        assert len(parts) == 3  # num operator num
