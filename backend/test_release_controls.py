import hashlib
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.check_dependency_audit import findings
from scripts.check_review_provenance import check, ROOT
from scripts.release_sources import source_paths


class ReleaseControlTests(unittest.TestCase):
    def test_dependency_exceptions_are_version_scoped_and_expire(self):
        report={'dependencies':[{'name':'example','version':'1.0','vulns':[{'id':'CVE-example'}]}]}
        policy={'exceptions':[{'package':'example','version':'1.0','advisories':['CVE-example'],
            'expires':'2026-12-09','reason':'Documented deployment applicability.'}]}
        rejected,excepted=findings(report,policy,date(2026,11,9))
        self.assertFalse(rejected)
        self.assertEqual(len(excepted),1)
        report['dependencies'][0]['version']='1.1'
        self.assertTrue(findings(report,policy,date(2026,11,9))[0])
        with self.assertRaises(ValueError):findings(report,policy,date(2026,12,9))

    def test_evidence_covers_all_backend_modules_and_lockfile(self):
        names=source_paths()
        self.assertIn('backend/model_metrics.py',names)
        self.assertIn('backend/prompt_context.py',names)
        self.assertIn('backend/requirements.lock',names)
        self.assertFalse(any(Path(name).name.startswith('test_') for name in names))
        digest=lambda value:hashlib.sha256(value.encode()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            dataset=Path(folder)/'data.json'; dataset.write_text('[{"id":"one"}]')
            report=dict(mode='live',dataset_sha256=digest(dataset.read_text()),
                cases=[{'id':'one','run_id':'one:1'}],release_gate={'passed':True},
                source_sha256={name:digest((ROOT/name).read_text(encoding='utf-8')) for name in names})
            self.assertEqual(check(report,dataset),[])
            report['source_sha256']['backend/model_metrics.py']='old'
            self.assertTrue(any('model_metrics.py' in error for error in check(report,dataset)))
