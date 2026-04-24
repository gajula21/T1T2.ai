"""
Rate limiting middleware for BandBoost.

Two layers:
  1. RPM (requests per minute) — sliding window in Redis.
  2. Daily evaluation quota — per-user daily counter in Redis.

Both limits are completely independent: hitting RPM does not consume daily quota.
"""

import logging
from datetime import datetime, timezone, timedelta

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Base class for rate limit violations."""

    def __init__(self, message: str, retry_after: int = 0, quota_remaining: int = -1):
        self.message = message
        self.retry_after = retry_after
        self.quota_remaining = quota_remaining
        super().__init__(message)


class RPMLimitError(RateLimitError):
    """Raised when a user breaches the requests-per-minute limit."""
    pass


class DailyQuotaError(RateLimitError):
    """Raised when a user has exhausted their daily evaluation quota."""
    pass


# ─────────────────────────────────────────────
# IST midnight reset helpers
# ─────────────────────────────────────────────
def _ist_midnight_utc() -> datetime:
    """Returns the next midnight in IST (UTC+5:30) as UTC datetime."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    midnight_ist = (now_ist + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return midnight_ist.astimezone(timezone.utc)


def _seconds_until_ist_midnight() -> int:
    """Seconds until the next IST midnight."""
    now_utc = datetime.now(timezone.utc)
    return int((_ist_midnight_utc() - now_utc).total_seconds())


def _ist_date_str() -> str:
    """Returns the current date in IST as 'YYYYMMDD'."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y%m%d")


# ─────────────────────────────────────────────
# Layer 1: RPM guard
# ─────────────────────────────────────────────
def check_rpm(user_id: str) -> None:
    """
    Enforces RPM_LIMIT requests per minute per user.
    Uses a sliding window in Redis with 1-minute TTL.
    Raises RPMLimitError if the limit is breached.
    """
    limit = getattr(settings, "RPM_LIMIT", 10)
    window_key = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    cache_key = f"rpm:{user_id}:{window_key}"

    current = cache.get(cache_key, 0)
    if current >= limit:
        raise RPMLimitError(
            message=f"Rate limit exceeded: {limit} requests per minute.",
            retry_after=60,
        )

    # Increment counter; set TTL to 65s to cover clock drift
    pipe_value = cache.get_or_set(cache_key, 0, timeout=65)
    cache.incr(cache_key)
    logger.debug("RPM check: user=%s, window=%s, count=%d/%d", user_id, window_key, current + 1, limit)


# ─────────────────────────────────────────────
# Layer 2: Daily evaluation quota
# ─────────────────────────────────────────────
def check_daily_quota(user_id: str) -> int:
    """
    Enforces DAILY_EVAL_LIMIT evaluations per day per user.
    Counter resets at midnight IST.
    Returns the number of remaining evaluations for today.
    Raises DailyQuotaError if the limit is reached.
    """
    limit = getattr(settings, "DAILY_EVAL_LIMIT", 5)
    date_str = _ist_date_str()
    cache_key = f"dailyeval:{user_id}:{date_str}"

    current = cache.get(cache_key, 0)
    remaining = limit - current

    if remaining <= 0:
        seconds_until_reset = _seconds_until_ist_midnight()
        raise DailyQuotaError(
            message=f"Daily evaluation limit of {limit} reached. Resets at midnight IST.",
            retry_after=seconds_until_reset,
            quota_remaining=0,
        )

    return remaining


def consume_daily_quota(user_id: str) -> int:
    """
    Increments the daily evaluation counter.
    Returns the new remaining count.
    Should be called AFTER the evaluation is successfully queued.
    """
    limit = getattr(settings, "DAILY_EVAL_LIMIT", 5)
    date_str = _ist_date_str()
    cache_key = f"dailyeval:{user_id}:{date_str}"
    ttl = _seconds_until_ist_midnight() + 3600  # +1h buffer

    # Atomic increment
    if cache.get(cache_key) is None:
        cache.set(cache_key, 1, timeout=ttl)
        new_count = 1
    else:
        new_count = cache.incr(cache_key)

    remaining = max(0, limit - new_count)
    logger.info(
        "Daily quota consumed: user=%s, date=%s, used=%d/%d",
        user_id, date_str, new_count, limit
    )
    return remaining


def get_quota_status(user_id: str) -> dict:
    """
    Returns the current quota status for a user.
    Used by the /api/quota endpoint.
    """
    limit = getattr(settings, "DAILY_EVAL_LIMIT", 5)
    date_str = _ist_date_str()
    cache_key = f"dailyeval:{user_id}:{date_str}"

    used = cache.get(cache_key, 0)
    remaining = max(0, limit - used)
    seconds_until_reset = _seconds_until_ist_midnight()

    return {
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "resets_in_seconds": seconds_until_reset,
        "resets_at_ist_midnight": True,
    }
