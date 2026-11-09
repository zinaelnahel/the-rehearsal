"""Session-local numeric model metrics; never store prompts, replies or identifiers."""
import time
from langchain_core.callbacks import BaseCallbackHandler


def count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


class ModelMetrics(BaseCallbackHandler):
    """One request, including token usage when parsing subsequently fails.

    Usage is provider-reported, not estimated. Missing reports remain missing;
    budget reservations are a separate ceiling and are never treated as billing.
    """
    run_inline = True

    def __init__(self, session):
        self.session = session
        self.input_tokens = None
        self.output_tokens = None

    def on_llm_end(self, response, **kwargs):
        usage = (response.llm_output or {}).get('token_usage') or {}
        self.input_tokens = count(usage.get('prompt_tokens'))
        self.output_tokens = count(usage.get('completion_tokens'))
        if self.input_tokens is None or self.output_tokens is None:
            # Newer adapters normalize usage on AIMessage rather than llm_output.
            generations = response.generations
            message = getattr(generations[0][0], 'message', None) if generations and generations[0] else None
            usage = getattr(message, 'usage_metadata', None) or {}
            self.input_tokens = count(usage.get('input_tokens'))
            self.output_tokens = count(usage.get('output_tokens'))

    def __enter__(self):
        self.started = time.monotonic()
        return self

    def __exit__(self, error_type, error, traceback):
        if self.session is None:
            return False
        stats = self.session.setdefault('model_usage', dict(
            requests=0, failures=0, elapsed_ms=0, input_tokens=0, output_tokens=0,
            usage_reports=0, missing_usage_reports=0))
        stats['requests'] += 1
        stats['failures'] += int(error_type is not None)
        stats['elapsed_ms'] += max(0, round((time.monotonic()-self.started)*1000))
        reported = self.input_tokens is not None and self.output_tokens is not None
        stats['usage_reports' if reported else 'missing_usage_reports'] += 1
        if reported:
            stats['input_tokens'] += self.input_tokens
            stats['output_tokens'] += self.output_tokens
        return False
