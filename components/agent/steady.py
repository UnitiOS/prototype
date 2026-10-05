"""steady — a call the provider failed for a moment is made again, briefly.

Providers fail now and then for reasons that are theirs: an internal error, a
moment of overload, a connection that drops. That is not the model being
wrong, and a request should not end over it. So a call that fails that way is
made again, at most `AGAIN` times, after a short wait; each time is written to
the watch. A failure that is not the provider's — a refused request, a bad
argument — is not retried: making it again would fail again, and cost again.

Nothing here names a provider: it wraps the framework's call to any model.
"""

import asyncio

import httpx
import httpx2
from pydantic_ai.capabilities import Hooks
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError

AGAIN = 2
WAIT = (2.0, 8.0)
BUSY = (408, 429, 500, 502, 503, 504)


def passing(exc):
    """Whether a failure is the provider's for a moment, and worth one more try."""
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in BUSY
    if isinstance(exc, (httpx.TransportError, httpx2.TransportError, TimeoutError)):
        return True
    cause = exc.__cause__
    return isinstance(exc, ModelAPIError) and cause is not None and passing(cause)


def steady(part, watch=None):
    """Hooks that make a failed call again, for one part."""
    hooks = Hooks()

    @hooks.on.model_request
    async def _again(ctx, *, request_context, handler):
        for n in range(AGAIN + 1):
            try:
                return await handler(request_context)
            except Exception as exc:
                if n == AGAIN or not passing(exc):
                    raise
                if watch:
                    watch.note(f"{part} call {ctx.run_step} failed ({type(exc).__name__}: "
                               f"{str(exc)[:200]}); trying again in {WAIT[n]:.0f} s")
                await asyncio.sleep(WAIT[n])

    return hooks


__all__ = ["AGAIN", "BUSY", "passing", "steady"]
