"""Upload bundled fictional fixtures and run a traced LangSmith experiment.

Explicit invocation uploads synthetic data. --live/--judge incur provider calls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from langsmith import Client
from langsmith.evaluation import evaluate
from unittest.mock import patch
from backend import main as api
from backend.observability import synthetic_evaluation, trace_scope
from scripts.evaluate_rag import run_case, RUBRICS
from scripts.evaluate_agent_tools import run_case as run_tool_case


def regression(run, example):
    checks = run.outputs.get('checks', {})
    return {'key': 'deterministic_checks', 'score': int(bool(checks) and all(checks.values()))}


def judge_metric(metric):
    def score(run, example):
        grade = run.outputs.get('judge', {}).get(metric, {})
        return {'key': metric, 'score': int(grade.get('passed', False)),
                'comment': grade.get('explanation', 'No model judge result')}
    score.__name__ = metric
    return score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--judge', action='store_true')
    parser.add_argument('--suite', choices=['rag', 'tools'], default='rag')
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/langsmith-evaluation.json')
    args = parser.parse_args()
    if args.suite == 'tools' and (not args.live or args.judge):
        parser.error('Tool-selection experiments require --live and do not use --judge.')
    if not os.getenv('LANGSMITH_API_KEY'):
        parser.error('Set LANGSMITH_API_KEY before running this synthetic upload.')
    if (args.live or args.judge) and not os.getenv('OPENAI_API_KEY'):
        parser.error('--live/--judge require OPENAI_API_KEY')
    fixture = ROOT / ('evaluation/agent-tool-dataset.json' if args.suite == 'tools' else 'evaluation/rag-dataset.json')
    cases = json.loads(fixture.read_text(encoding='utf-8'))
    revision = hashlib.sha256(fixture.read_bytes()).hexdigest()
    dataset_name = 'rehearsal-fictional-' + args.suite + '-' + revision[:12]
    client = Client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name,
            description='Bundled fictional EN/DE/ES fixtures; no user data.')
        client.create_examples(dataset_id=dataset.id, inputs=cases,
            outputs=[({'expected_tool': case['expected_tool']} if args.suite == 'tools' else
                      {'reference_answer': case['reference_answer'],
                       'expected_status': case['expected_status']}) for case in cases])

    def target(inputs):
        started = time.monotonic()
        with synthetic_evaluation(), trace_scope(), TestClient(api.app) as http:
            row = run_tool_case(http, inputs) if args.suite == 'tools' else run_case(http, inputs, args.judge)
        row['elapsed_seconds'] = round(time.monotonic() - started, 3)
        return row

    metadata = {'dataset_sha256': revision, 'suite': args.suite, 'mode': 'live' if args.live else 'demo',
        'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), 'embedding': 'local-hash-512-v1',
        'vector_store': os.getenv('VECTOR_STORE', 'chroma'), 'top_k': 4,
        'chunk_size': 700, 'chunk_overlap': 100, 'judge_enabled': args.judge,
        'agent_enabled': args.live and os.getenv('REHEARSAL_AGENT_ENABLED', 'true') == 'true',
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ('backend/main.py', 'backend/live.py', 'backend/agent.py',
                         'backend/retrieval.py', 'backend/context.py')}}
    with patch.object(api, 'LIVE', args.live), patch.dict(os.environ, {'API_PROXY_TOKEN': ''}):
        experiment = evaluate(target, data=dataset_name, client=client, max_concurrency=1,
            experiment_prefix=os.getenv('LANGSMITH_PROJECT', 'the-rehearsal-evaluation'),
            metadata=metadata, evaluators=[regression] +
                ([judge_metric(metric) for metric in RUBRICS] if args.judge else []))
        rows = list(experiment)
    passed = len(rows) == len(cases) and all(
        row['run'].outputs and row['run'].outputs.get('passed') and
        all(result.score == 1 for result in row['evaluation_results']['results']) for row in rows)
    report = {'experiment_name': experiment.experiment_name, 'dataset': dataset_name,
        'metadata': metadata, 'passed': passed, 'cases': [
            {'run_id': str(row['run'].id), 'outputs': row['run'].outputs,
             'scores': [{'key': result.key, 'score': result.score}
                        for result in row['evaluation_results']['results']]} for row in rows]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Experiment:', experiment.experiment_name)
    print('Report:', args.output)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
