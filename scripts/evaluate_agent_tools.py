"""Paid real-model selection of several read-only tools on fictional fixtures."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from backend import main as api
from backend.agent import prepare


def require(response):
    if response.status_code != 200:
        raise RuntimeError(f'API returned HTTP {response.status_code}')
    return response.json()


def run_case(client, case):
    sid = require(client.post('/api/sessions', json={'text': 'Monthly rent is 1420 euros. Utilities are included.'}))['id']
    path = '/api/sessions/' + sid
    started = time.monotonic()
    try:
        # Fixed fictional setup avoids paying for unrelated mission generation.
        with patch.object(api, 'LIVE', False):
            require(client.post(path + '/mission', json={'scenario': 'apartment', 'language': 'English',
                'feedback_language': 'English', 'level': 'Everyday'}))
            require(client.post(path + '/start', json={'goals': ['Ask the rent', 'Ask whether utilities are included']}))
        session = api.sessions[sid]
        before = deepcopy({'mission': session['mission'], 'turns': session['turns']})
        tools, docs = prepare(session, case['question'], api.search(session, case['question']),
                              api.agent_model, api.search, api.evidence)
        selected = [item['tool'] for item in tools]
        checks = {'expected_tool_selected': case['expected_tool'] in selected,
            'read_only_state': before == {'mission': session['mission'], 'turns': session['turns']},
            'bounded_calls': len(selected) <= 4, 'session_sources': all(
                doc.page_content in 'Monthly rent is 1420 euros. Utilities are included.' for doc in docs)}
        return {'id': case['id'], 'question': case['question'], 'tools': selected, 'checks': checks,
                'elapsed_seconds': round(time.monotonic() - started, 3), 'passed': all(checks.values())}
    finally:
        require(client.delete(path))
        if client.get(path + '/status').status_code != 404:
            raise RuntimeError('Session deletion verification failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/agent-tools-evaluation.json')
    args = parser.parse_args()
    if not os.getenv('OPENAI_API_KEY'):
        parser.error('OPENAI_API_KEY is required; up to six paid model calls.')
    fixture = ROOT / 'evaluation/agent-tool-dataset.json'
    report = {'run_at_utc': datetime.now(timezone.utc).isoformat(),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), 'cases': [], 'passed': False,
        'dataset_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ('backend/main.py', 'backend/agent.py', 'backend/retrieval.py', 'scripts/evaluate_agent_tools.py')}}
    before = len(api.model_calls)
    with patch.dict(os.environ, {'API_PROXY_TOKEN': ''}), TestClient(api.app) as client:
        for case in json.loads(fixture.read_text(encoding='utf-8')):
            try:
                row = run_case(client, case)
            except Exception as error:
                row = {'id': case['id'], 'passed': False, 'error_type': type(error).__name__}
            report['cases'].append(row)
            print(case['id'], 'PASS' if row['passed'] else 'FAIL', flush=True)
    report['provider_calls'] = len(api.model_calls) - before
    report['passed'] = all(row['passed'] for row in report['cases'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Report:', args.output)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
