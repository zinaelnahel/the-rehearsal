"""Offline size comparison on fictional dialogue, not a token/cost benchmark."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.prompt_context import dialogue_history


def evaluate():
    rows = []
    for language, suffix in [('English', '.en'), ('German', '.de'), ('Spanish', '')]:
        source = (ROOT / 'samples' / f'apartment{suffix}.txt').read_text(encoding='utf-8')
        turns = []
        # Repeated cited answers expose the historical-source duplication.
        # This deliberately measures payload shape, not generation quality.
        for _ in range(10):
            turns.extend([{'role': 'user', 'content': 'Please clarify the source details.'},
                          {'role': 'assistant', 'content': 'Let us check the listing. [1]',
                           'sources': [{'id': '1', 'text': source}], 'id': 'synthetic-reply'}])
        for limit in [6, 16, None]:
            before = len(json.dumps(turns if limit is None else turns[-limit:], ensure_ascii=False).encode())
            after = len(json.dumps(dialogue_history(turns, limit), ensure_ascii=False).encode())
            rows.append({'language': language, 'history_limit': limit,
                         'before_bytes': before, 'after_bytes': after,
                         'history_bytes_reduction_percent': round(100 * (before-after) / before, 1)})
    return {'synthetic': True, 'measurement': 'UTF-8 serialized history bytes only; excludes prompts, schemas and current retrieval; not token counts or billing savings',
            'cases': rows}


if __name__ == '__main__':
    report = evaluate()
    target = ROOT / '.runtime' / 'prompt-context-evaluation.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
