"""Reject new advisories; expose narrowly scoped, dated deployment exceptions."""
import argparse
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def findings(report, policy, today=None):
    today=today or date.today()
    allowed={}
    for item in policy['exceptions']:
        if date.fromisoformat(item['expires']) <= today:
            raise ValueError('Expired dependency exception: '+item['package'])
        if not item.get('reason','').strip():
            raise ValueError('Dependency exceptions require a reason')
        for advisory in item['advisories']:
            allowed[(item['package'],item['version'],advisory)]=item['reason']
    rejected=set()
    excepted=set()
    for dependency in report['dependencies']:
        if dependency.get('skip_reason'):
            rejected.add((dependency['name'],'unknown','dependency not audited'))
        for issue in dependency.get('vulns',[]):
            key=(dependency['name'],dependency['version'],issue['id'])
            (excepted if key in allowed else rejected).add(key)
    return sorted(rejected),sorted(excepted)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/dependency-audit.json')
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # A tool/registry failure is not a clean audit. pip-audit returns 1 for
    # vulnerability findings; other exit codes and absent reports are failures.
    result=subprocess.run([sys.executable,'-m','pip_audit','--disable-pip','--no-deps',
        '--require-hashes','-r',str(ROOT/'backend/requirements.lock'),
        '--format','json','--output',str(args.output)])
    if result.returncode not in (0,1):return result.returncode
    report=json.loads(args.output.read_text(encoding='utf-8'))
    if not report.get('dependencies'):raise ValueError('No audited dependencies')
    rejected,excepted=findings(report,json.loads((ROOT/'security/dependency-exceptions.json').read_text()))
    for key in excepted:print('Documented temporary exception:',*key)
    for key in rejected:print('Unresolved dependency finding:',*key)
    print(f'{len(rejected)} unexcepted findings; {len(excepted)} documented temporary exceptions.')
    return int(bool(rejected))


if __name__=='__main__':raise SystemExit(main())
