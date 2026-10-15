"""steady — a call the provider failed for a moment is made again, briefly.

Providers fail now and then for reasons that are theirs: an internal error, a
moment of overload, a connection that drops. That is not the model being
wrong, and a request should not end over it. So a call that fails that way is
made again, at most `AGAIN` times, after a short wait; each time is written to
the watch. A failure that is not the provider's — a refused request, a bad
argument — is not retried: making it again would fail again, and cost again.

A call that hangs is a provider that fails. The time a call may take
(`timeout`, from the configuration) is held here, on our side, around each try
and whatever the provider's library retries inside it: a provider's own limit
was seen not to hold (calls of 102 to 397 s against 90). A try cut short is
made again like any failure of the provider's.

A call that still fails after its tries fails as the provider's
(`ModelAPIError`), whatever the library underneath raised, so the request
ends as the provider's failure — kept, and said to the person — rather than
escaping as an error nobody keeps. That holds for the accountant too, whose
call is made inside one of the builder's.

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


class Hung(TimeoutError):
    """A try that did not answer within the time a call may take."""


def passing(exc):
    """Whether a failure is the provider's for a moment, and worth one more try."""
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in BUSY
    if isinstance(exc, (httpx.TransportError, httpx2.TransportError, TimeoutError)):
        return True
    cause = exc.__cause__
    return isinstance(exc, ModelAPIError) and cause is not None and passing(cause)


def steady(part, watch=None, timeout=None):
    """Hooks that make a failed call again, for one part, each try cut at
    `timeout` seconds when one is given."""
    hooks = Hooks()

    async def _try(handler, request_context):
        if timeout is None:
            return await handler(request_context)
        try:
            return await asyncio.wait_for(handler(request_context), timeout)
        except asyncio.TimeoutError:
            raise Hung(f"did not answer within {timeout:g} s") from None

    @hooks.on.model_request
    async def _again(ctx, *, request_context, handler):
        for n in range(AGAIN + 1):
            try:
                return await _try(handler, request_context)
            except Exception as exc:
                if not passing(exc):
                    raise
                said = f"{type(exc).__name__}: {str(exc)[:200]}"
                if n == AGAIN:
                    if watch:
                        watch.note(f"{part} call {ctx.run_step} failed ({said}); "
                                   f"no more tries")
                    if isinstance(exc, ModelAPIError):
                        raise
                    raise ModelAPIError(getattr(ctx.model, "model_name", part),
                                        said) from exc
                if watch:
                    watch.note(f"{part} call {ctx.run_step} failed ({said}); "
                               f"trying again in {WAIT[n]:.0f} s")
                await asyncio.sleep(WAIT[n])

    return hooks


__all__ = ["AGAIN", "BUSY", "Hung", "passing", "steady"]
