"""Offline multilingual speaker-ownership regression; never calls a provider."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.test_family_roles import FamilyRoleMatrixTests


class Results(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.cases=[]

    def addSubTest(self,test,subtest,error):
        super().addSubTest(test,subtest,error)
        self.cases.append({**dict(subtest.params),'passed':error is None})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.runtime/role-boundaries.json')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rehearsal-role-matrix-') as folder,patch.dict(os.environ,{
        'OPENAI_API_KEY':'','LANGSMITH_TRACING':'false','LANGCHAIN_TRACING_V2':'false',
        'FEEDBACK_DB_PATH':str(Path(folder)/'feedback.sqlite3')}):
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(FamilyRoleMatrixTests)
        result=unittest.TextTestRunner(verbosity=1,resultclass=Results).run(suite)
    groups={}
    for language in ('English','German','Spanish'):
        rows=[row for row in result.cases if row['language']==language]
        groups[language]={
            'styles':sorted({row['style'] for row in rows}),
            'cases':len(rows),'passed':sum(row['passed'] for row in rows),
            'reversed_replies_blocked':sum(row['passed'] and row['invalid'] for row in rows),
            'valid_requester_replies_allowed':sum(row['passed'] and not row['invalid'] for row in rows)}
    report={
        'run_at_utc':datetime.now(timezone.utc).isoformat(),
        'kind':'offline deterministic regression with mocked model generation and an approving reviewer',
        'provider_calls':0,'live_model_tested':False,
        'scope':'Fictional family requester versus learner declining help; not general role reliability.',
        'passed':result.wasSuccessful(),'test_methods':result.testsRun,
        'case_count':len(result.cases),'languages':groups,
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
            'backend/family_boundary.py','backend/live.py','backend/test_family_roles.py',
            'evaluation/family-role-regressions.json','scripts/evaluate_role_boundaries.py')},
        'cases':result.cases}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(groups,indent=2))
    print('Report:',args.output)
    if not result.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':main()
