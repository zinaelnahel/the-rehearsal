"""Explicit tracing boundary: only the local synthetic evaluation runner opts in."""
from contextlib import contextmanager
from contextvars import ContextVar
from langsmith import tracing_context

_evaluation = ContextVar('synthetic_evaluation', default=False)


@contextmanager
def synthetic_evaluation():
    token = _evaluation.set(True)
    try:
        yield
    finally:
        _evaluation.reset(token)


def trace_scope():
    # Incoming headers never enable tracing. Context propagates through TestClient
    # and asyncio.to_thread, but normal network requests have no evaluation token.
    return tracing_context(enabled=_evaluation.get())
