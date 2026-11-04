"""Lossless dialogue projection: current retrieval supplies source evidence."""


def dialogue_history(turns, limit):
    """Keep dialogue verbatim without replaying stored source payloads.

    Citation markers in content remain intact. Historical sources are not current
    evidence; generation and review must use the separately retrieved passages.
    Never mutate the session turns used by the UI, download or evidence checks.
    """
    selected = turns if limit is None else turns[-limit:]
    return [{'role': turn['role'], 'content': turn['content']}
            for turn in selected]
