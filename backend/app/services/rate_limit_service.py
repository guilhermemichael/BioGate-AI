from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import time

from fastapi import HTTPException, status


@dataclass(slots=True)
class RateLimitResult:
    key: str
    current_count: int
    limit: int
    retry_after_seconds: int | None


class RateLimitService:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def enforce(
        self,
        *,
        scope: str,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        bucket_key = f"{scope}:{key}"
        now = time()
        with self._lock:
            bucket = self._events[bucket_key]
            while bucket and (now - bucket[0]) >= window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {scope}. Retry in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)
            return RateLimitResult(
                key=bucket_key,
                current_count=len(bucket),
                limit=limit,
                retry_after_seconds=None,
            )


rate_limiter = RateLimitService()
