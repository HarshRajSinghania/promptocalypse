import pytest
from fastapi import HTTPException
from app.rate_limiter import KeySubmissionRateLimiter

def test_key_submission_rate_limiter_base():
    limiter = KeySubmissionRateLimiter(base_cooldown=2.0)
    
    # attempt 1
    limiter.check("user1")
    limiter.record_attempt("user1", False)
    
    # attempt 2 too fast
    with pytest.raises(HTTPException) as exc:
        limiter.check("user1")
    assert exc.value.status_code == 429
    
    # manually advance time
    limiter._state["user1"] = (limiter._state["user1"][0] - 3.0, limiter._state["user1"][1])
    
    # attempt 2 ok
    limiter.check("user1")
    limiter.record_attempt("user1", False)
    
    # attempt 3 too fast
    with pytest.raises(HTTPException):
        limiter.check("user1")
        
    limiter._state["user1"] = (limiter._state["user1"][0] - 3.0, limiter._state["user1"][1])
    
    # attempt 3 ok, fails again, reaches 3 max failures
    limiter.check("user1")
    limiter.record_attempt("user1", False)
    
    # attempt 4 too fast, should enforce lockout (30s)
    limiter._state["user1"] = (limiter._state["user1"][0] - 3.0, limiter._state["user1"][1])
    with pytest.raises(HTTPException) as exc:
        limiter.check("user1")
    assert exc.value.status_code == 429
    
    # advance by 31s
    limiter._state["user1"] = (limiter._state["user1"][0] - 31.0, limiter._state["user1"][1])
    limiter.check("user1")
    limiter.record_attempt("user1", True) # Correct! Resets failures
    
    # Next attempt only needs 2 seconds
    limiter._state["user1"] = (limiter._state["user1"][0] - 3.0, limiter._state["user1"][1])
    limiter.check("user1")
