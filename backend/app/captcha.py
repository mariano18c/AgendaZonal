"""
Simple CAPTCHA implementation for registration.
Generates math problems to prevent automated bot registrations.
"""
import random
import string
import hashlib
import time
from dataclasses import dataclass


@dataclass
class CaptchaChallenge:
    """Represents a CAPTCHA challenge."""
    id: str
    question: str
    answer_hash: str
    expires_at: float
    
    def verify(self, answer: str) -> bool:
        """Verify the answer against the stored hash."""
        if time.time() > self.expires_at:
            return False
        
        # Hash the provided answer with the challenge ID for extra security
        answer_str = f"{self.id}:{answer.strip().lower()}"
        answer_hash = hashlib.sha256(answer_str.encode()).hexdigest()
        
        return answer_hash == self.answer_hash


class CaptchaManager:
    """Manages CAPTCHA challenges."""
    
    CHALLENGES: dict[str, CaptchaChallenge] = {}
    CLEANUP_INTERVAL = 300  # 5 minutes
    LAST_CLEANUP = 0
    
    @classmethod
    def generate(cls) -> CaptchaChallenge:
        """Generate a new CAPTCHA challenge."""
        # Clean up old challenges periodically
        cls._cleanup()
        
        # Generate random math problem
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            answer = a + b
            question = f"{a} + {b} = ?"
        elif operation == '-':
            a = random.randint(5, 30)
            b = random.randint(1, a)  # Ensure positive result
            answer = a - b
            question = f"{a} - {b} = ?"
        else:  # multiplication (easier numbers)
            a = random.randint(2, 10)
            b = random.randint(2, 10)
            answer = a * b
            question = f"{a} × {b} = ?"
        
        # Generate unique ID
        challenge_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # Hash the answer with ID
        answer_str = f"{challenge_id}:{answer}"
        answer_hash = hashlib.sha256(answer_str.encode()).hexdigest()
        
        # Create challenge (expires in 5 minutes)
        challenge = CaptchaChallenge(
            id=challenge_id,
            question=question,
            answer_hash=answer_hash,
            expires_at=time.time() + 300
        )
        
        cls.CHALLENGES[challenge_id] = challenge
        return challenge
    
    @classmethod
    def verify(cls, challenge_id: str, answer: str) -> bool:
        """Verify a CAPTCHA answer."""
        challenge = cls.CHALLENGES.get(challenge_id)
        if not challenge:
            return False
        
        result = challenge.verify(answer)
        
        # Remove challenge after verification (one-time use)
        if challenge_id in cls.CHALLENGES:
            del cls.CHALLENGES[challenge_id]
        
        return result
    
    @classmethod
    def _cleanup(cls):
        """Remove expired challenges."""
        now = time.time()
        if now - cls.LAST_CLEANUP < cls.CLEANUP_INTERVAL:
            return
        
        cls.LAST_CLEANUP = now
        expired = [k for k, v in cls.CHALLENGES.items() if now > v.expires_at]
        for k in expired:
            del cls.CHALLENGES[k]
