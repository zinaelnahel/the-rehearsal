"""Reject stale or offline reports before a production quality gate."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]


def check(report, dataset):
    errors=[]
    if report.get('mode')!='live':errors.append('Production requires a live-model benchmark')
    digest=lambda text:hashlib.sha256(text.encode('utf-8')).hexdigest()
    if report.get('dataset_sha256')!=digest(dataset.read_text(encoding='utf-8')):
        errors.append('Dataset changed after evaluation')
    expected={r['id'] for r in json.loads(dataset.read_text(encoding='utf-8'))}
    actual={r.get('id') for r in report.get('cases',[])}
    run_ids=[r.get('run_id') for r in report.get('cases',[])]
    if expected!=actual or len(set(run_ids))!=len(run_ids):
        errors.append('Benchmark cases are missing, unexpected or duplicated')
    required=('backend/main.py','backend/live.py','backend/agent.py','backend/retrieval.py',
              'backend/demo_answers.py','backend/source_conflicts.py','backend/context.py',
              'backend/content.py','scripts/evaluate_quality.py')
    for name in required:
        if report.get('source_sha256',{}).get(name)!=digest((ROOT/name).read_text(encoding='utf-8')):
            errors.append('Code changed or was not recorded: '+name)
    if not report.get('release_gate',{}).get('passed'):errors.append('Human-reviewed release criteria did not pass')
    return errors


if __name__=='__main__':
    report=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    errors=check(report,ROOT/'evaluation/quality-release-dataset.json')
    for error in errors:print(error)
    raise SystemExit(1 if errors else 0)
