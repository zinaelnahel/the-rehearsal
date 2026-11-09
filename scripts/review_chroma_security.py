"""Manual advisory review with fresh upstream metadata; never extends exceptions."""
import argparse
from datetime import datetime,timezone,date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-report',type=Path,required=True,help='Fresh output from scripts/check_dependency_audit.py')
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/chroma-security-review.json')
    args=parser.parse_args()
    policy_path=ROOT/'security/dependency-exceptions.json'
    policy=json.loads(policy_path.read_text())
    exception=next(item for item in policy['exceptions'] if item['package']=='chromadb')
    audit=json.loads(args.audit_report.read_text(encoding='utf-8'))
    package=next(item for item in audit['dependencies'] if item['name']=='chromadb')
    issues={item['id']:item for item in package.get('vulns',[])}
    advisories={alias for issue in issues.values() for alias in issue.get('aliases',[]) if alias.startswith('GHSA-')}
    with httpx.Client(timeout=30,follow_redirects=True,headers={'User-Agent':'rehearsal-security-review'}) as client:
        response=client.get('https://pypi.org/pypi/chromadb/json');response.raise_for_status()
        latest=response.json()['info']['version']
        upstream=[]
        for identifier in sorted(advisories):
            response=client.get('https://api.github.com/advisories/'+identifier);response.raise_for_status()
            item=response.json()
            upstream.append({'id':item['ghsa_id'],'url':item['html_url'],'updated_at':item['updated_at'],
                'withdrawn_at':item.get('withdrawn_at'),'severity':item.get('severity'),
                'affected_packages':item.get('vulnerabilities',[])})
    verification=subprocess.run([sys.executable,'-m','unittest','backend.test_chroma_security','-q'],
        cwd=ROOT,capture_output=True,text=True)
    reasons=[]
    if verification.returncode:reasons.append('Architecture regression tests failed')
    if date.fromisoformat(exception['expires'])<=datetime.now(timezone.utc).date():reasons.append('Exception expired')
    if latest!=exception['version'] or package['version']!=exception['version']:reasons.append('Package version changed; reassess instead of reusing exception')
    if set(issues)!=set(exception['advisories']):reasons.append('Advisory set changed')
    if any(issue.get('fix_versions') for issue in issues.values()):reasons.append('Audit identifies a patched version')
    if any(item.get('withdrawn_at') or any(v.get('first_patched_version') for v in item['affected_packages']) for item in upstream):
        reasons.append('Upstream advisory status changed; review patch/withdrawal')
    report={'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'installed_locked_version':package['version'],
        'latest_pypi_version':latest,'unique_audit_advisories':sorted(issues),'raw_audit_findings':len(package.get('vulns',[])),
        'upstream':upstream,'exception_expiry_unchanged':exception['expires'],
        'policy_sha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        'lock_sha256':hashlib.sha256((ROOT/'backend/requirements.lock').read_bytes()).hexdigest(),
        'audit_sha256':hashlib.sha256(args.audit_report.read_bytes()).hexdigest(),
        'architecture_source_sha256':{name:hashlib.sha256((ROOT/name).read_text(encoding='utf-8').encode()).hexdigest()
            for name in ['backend/retrieval.py','backend/test_chroma_security.py',
                'scripts/check_dependency_audit.py','scripts/review_chroma_security.py']},
        'architecture_regressions':{'command':'python -m unittest backend.test_chroma_security -q','passed':verification.returncode==0},
        'assessment':'The reviewed Chroma HTTP server paths are not exposed by our embedded-only configuration. No claim that the package is vulnerability-free.',
        'controls':['Explicit Rust embedded adapter; environment cannot select HTTP adapter.',
            'No Chroma server is started or proxied; source text cannot supply embedding-function configuration.',
            'Collections use server-owned hashed names and embedding_function=None.',
            'Public deployment remains memory retrieval; exception does not authorize a Chroma HTTP service.'],
        'needs_reassessment':bool(reasons),'reasons':reasons,'exception_renewed':False,
        'limitations':['Applicability assessment and regression tests, not an independent penetration test.',
            'Patch availability is a point-in-time observation; scheduled dependency checks remain required.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Locked/latest Chroma:',package['version'],latest)
    print('Unique advisories:',len(issues),'architecture checks passed:',verification.returncode==0)
    print('Exception expires unchanged:',exception['expires'],'needs reassessment:',bool(reasons))
    print('Report:',args.output)
    if reasons:raise SystemExit(1)


if __name__=='__main__':main()
