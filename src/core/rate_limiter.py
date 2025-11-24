"""
Rate Limiter - Control API call frequency
Implements token bucket algorithm for rate limiting
"""
import asyncio
import time
from typing import Dict


class RateLimiter:
    """
    Token bucket rate limiter for controlling API call frequency.

    Usage:
        limiter = RateLimiter(calls_per_minute=20)
        async with limiter:
            # Your API call here
            pass
    """

    def __init__(self, calls_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum number of calls allowed per minute
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute  # seconds between calls
        self.last_call_time = 0.0

    async def __aenter__(self):
        """Context manager entry - wait if needed"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass

    async def acquire(self):
        """Wait until rate limit allows next call"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            await asyncio.sleep(wait_time)

        self.last_call_time = time.time()


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different sites.

    Usage:
        limiters = MultiRateLimiter()
        limiters.set_limit(site_id=1, calls_per_minute=20)

        async with limiters.get(site_id=1):
            # Your API call here
            pass
    """

    def __init__(self):
        self.limiters: Dict[int, RateLimiter] = {}

    def set_limit(self, site_id: int, calls_per_minute: int):
        """
        Set rate limit for a specific site.

        Args:
            site_id: Site ID
            calls_per_minute: Maximum calls per minute for this site
        """
        self.limiters[site_id] = RateLimiter(calls_per_minute)

    def get(self, site_id: int) -> RateLimiter:
        """
        Get rate limiter for a site.
        Returns default 60 calls/min limiter if not configured.

        Args:
            site_id: Site ID

        Returns:
            RateLimiter instance
        """
        if site_id not in self.limiters:
            self.limiters[site_id] = RateLimiter(calls_per_minute=60)

        return self.limiters[site_id]
