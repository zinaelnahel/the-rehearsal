"""Lossless dialogue projection: current retrieval supplies source evidence."""


def dialogue_history(turns, limit):
    """Keep dialogue verbatim without replaying stored source payloads.

    Citation markers in content remain intact. Historical sources are not current
    evidence; generation and review must use the separately retrieved passages.
    Never mutate the session turns used by the UI, download or evidence checks.
    """
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError('History limit must be a nonnegative integer or None.')
    selected = turns if limit is None else turns[-limit:] if limit else []
    # A trimmed window should start with the learner, not an orphaned reply.
    if limit is not None and len(turns) > limit:
        while selected and selected[0]['role'] == 'assistant':
            selected = selected[1:]
    return [{'role': turn['role'], 'content': turn['content']}
            for turn in selected]
