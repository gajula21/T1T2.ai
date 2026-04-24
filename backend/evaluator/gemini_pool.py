"""
Gemini API Key Pool — round-robin rotation with per-key 429 tracking.

Usage:
    pool = get_flash_pool()      # GeminiKeyPool for Flash
    pool_lite = get_lite_pool()  # GeminiKeyPool for Flash-Lite
    client = pool.get_client()   # raises AllKeysExhaustedError if none left
    pool.mark_exhausted(key)     # call after receiving 429
"""

import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class AllKeysExhaustedError(Exception):
    """Raised when every key in the pool has been marked exhausted for today."""

    def __init__(self, reset_time: Optional[datetime] = None):
        self.reset_time = reset_time
        super().__init__(
            f"All Gemini API keys exhausted. Resets at {reset_time} Pacific time."
        )


class GeminiKeyPool:
    """
    Thread-safe round-robin pool of Gemini API keys.

    - Rotates keys on every request.
    - On HTTP 429, marks the offending key exhausted until midnight Pacific.
    - If all keys exhausted, raises AllKeysExhaustedError.
    """

    # Google's quota resets at midnight Pacific (UTC-8 / UTC-7 DST).
    # We use a conservative UTC-8 offset always for simplicity.
    GOOGLE_TZ_OFFSET = timedelta(hours=-8)

    def __init__(self, api_keys: list[str], model_name: str):
        if not api_keys:
            raise ValueError("GeminiKeyPool requires at least one API key.")

        self.model_name = model_name
        self._keys = list(api_keys)
        self._index = 0
        self._exhausted: dict[str, datetime] = {}  # key → exhausted_until datetime
        self._lock = threading.Lock()

        logger.info(
            "GeminiKeyPool initialised: model=%s, keys=%d", model_name, len(self._keys)
        )

    def _google_midnight(self) -> datetime:
        """Returns the next midnight in Google's Pacific timezone (UTC-8)."""
        pacific = timezone(self.GOOGLE_TZ_OFFSET)
        now_pacific = datetime.now(pacific)
        midnight = (now_pacific + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return midnight.astimezone(timezone.utc)

    def _is_exhausted(self, key: str) -> bool:
        """Returns True if the key is currently marked exhausted."""
        if key not in self._exhausted:
            return False
        if datetime.now(timezone.utc) >= self._exhausted[key]:
            del self._exhausted[key]
            return False
        return True

    def get_key(self) -> str:
        """
        Returns the next available API key using round-robin.
        Raises AllKeysExhaustedError if no keys are available.
        """
        with self._lock:
            start = self._index
            for _ in range(len(self._keys)):
                key = self._keys[self._index % len(self._keys)]
                self._index = (self._index + 1) % len(self._keys)
                if not self._is_exhausted(key):
                    return key
                _ = _  # suppress lint

            # All keys tried and exhausted
            reset_time = self._google_midnight()
            raise AllKeysExhaustedError(reset_time=reset_time)

    def get_client(self) -> genai.GenerativeModel:
        """
        Configures genai with the next available key and returns a model client.
        """
        key = self.get_key()
        genai.configure(api_key=key)
        return genai.GenerativeModel(model_name=self.model_name), key

    def mark_exhausted(self, key: str):
        """
        Mark a key as exhausted until midnight Pacific time.
        Call this when you receive a 429 from Google.
        """
        with self._lock:
            reset = self._google_midnight()
            self._exhausted[key] = reset
            logger.warning(
                "Gemini key marked exhausted. model=%s, resets_at=%s",
                self.model_name,
                reset.isoformat(),
            )

    @property
    def available_count(self) -> int:
        """Number of currently available (non-exhausted) keys."""
        with self._lock:
            return sum(
                1 for k in self._keys if not self._is_exhausted(k)
            )

    @property
    def total_count(self) -> int:
        return len(self._keys)


# ─────────────────────────────────────────────
# Singleton instances (created once at startup)
# ─────────────────────────────────────────────
_flash_pool: Optional[GeminiKeyPool] = None
_lite_pool: Optional[GeminiKeyPool] = None
_pool_lock = threading.Lock()


def _get_keys() -> list[str]:
    keys = list(settings.GEMINI_API_KEYS)
    return [k.strip() for k in keys if k.strip()]


def get_flash_pool() -> GeminiKeyPool:
    """Returns the singleton GeminiKeyPool for gemini-2.0-flash (supports image input)."""
    global _flash_pool
    if _flash_pool is None:
        with _pool_lock:
            if _flash_pool is None:
                keys = _get_keys()
                if not keys:
                    raise ValueError(
                        "GEMINI_API_KEYS is empty. Add keys to your .env file."
                    )
                _flash_pool = GeminiKeyPool(
                    api_keys=keys,
                    model_name="gemini-3-flash-preview",
                )
    return _flash_pool


def get_lite_pool() -> GeminiKeyPool:
    """Returns the singleton GeminiKeyPool for gemini-2.0-flash-lite."""
    global _lite_pool
    if _lite_pool is None:
        with _pool_lock:
            if _lite_pool is None:
                keys = _get_keys()
                if not keys:
                    raise ValueError(
                        "GEMINI_API_KEYS is empty. Add keys to your .env file."
                    )
                _lite_pool = GeminiKeyPool(
                    api_keys=keys,
                    model_name="gemini-2.0-flash-lite",
                )
    return _lite_pool

