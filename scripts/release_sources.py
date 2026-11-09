"""One manifest for writing and validating live evaluation provenance."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_paths(root=ROOT):
    backend = [p.relative_to(root).as_posix() for p in (root/'backend').rglob('*.py')
               if not p.name.startswith('test_') and '__pycache__' not in p.parts]
    return sorted(backend + ['backend/requirements.txt','backend/requirements.lock',
        'scripts/evaluate_quality.py','scripts/check_review_provenance.py','scripts/release_sources.py'])
