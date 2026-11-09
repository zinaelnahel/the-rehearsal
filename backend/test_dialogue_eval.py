"""Evaluation integrity and real endpoint replay; no provider calls."""
from copy import deepcopy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from scripts import evaluate_dialogue as ev
from backend import main as api


class DialogueEvalTests(unittest.TestCase):
    def setUp(self):
        self.cases = ev.load_cases(ev.ROOT/'evaluation/dialogue-dataset.json')
        self.case = self.cases[0]
        self.row = {'id': self.case['id'], 'run_id': self.case['id']+':1',
                    'answer': '¿Cómo aprendiste algo nuevo en tu trabajo?',
                    'retrieved_passages': [], 'judge': None, 'human': None}
        self.row['output_sha256'] = ev.digest({'case': self.case, 'answer': self.row['answer'],
                                               'retrieved_passages': []})
        self.ratings = {d: {'verdict': 'pass', 'reason': 'Addresses the learner in context.',
                           'candidate_quote': ''} for d in ev.DIMENSIONS}
        self.report = {'report_id': 'report-1', 'mode': 'live', 'fixtures': [self.case],
                       'dataset_sha256': 'dataset-1', 'rubric_sha256': 'rubric-1',
                       'judge_model': 'separate-evaluator', 'cases': [self.row]}
        self.review = {'run_id': self.row['run_id'], 'report_id': 'report-1',
                       'output_sha256': self.row['output_sha256'], 'reviewer': 'test-reviewer',
                       'ratings': self.ratings}

    def test_dataset_has_multilingual_failures_and_positive_controls(self):
        self.assertEqual({c['language'] for c in self.cases}, {'English', 'German', 'Spanish'})
        self.assertTrue(any(not c['author_expected_defects'] for c in self.cases))
        self.assertTrue(any('continuity' in c['author_expected_defects'] for c in self.cases))

    def test_judge_is_blind_to_labels_references_and_app_decisions(self):
        payload = ev.judge_payload(self.case, {**self.row, 'withheld': True,
                                              'judge': self.ratings, 'prompt_version': 'new'})
        self.assertEqual(payload['history'], self.case['history'])
        self.assertEqual(payload['latest_learner_turn'], self.case['learner'])
        self.assertEqual(set(payload), {'scenario', 'partner_role', 'conversation_language',
                                      'source', 'history', 'latest_learner_turn', 'candidate', 'retrieved_passages'})

    def test_missing_and_uncertain_judgments_are_not_passes(self):
        row = deepcopy(self.row)
        row['judge'] = deepcopy(self.ratings)
        row['judge']['continuity']['verdict'] = 'uncertain'
        metrics = ev.summarize([row, self.row])
        self.assertIsNone(metrics['judge']['continuity']['pass_rate_decided'])
        self.assertEqual(metrics['judge']['continuity']['unreviewed'], 1)
        self.assertFalse(metrics['human_review_complete'])
        self.assertIsNone(metrics['calibration']['exact_agreement'])

    def test_invalid_judge_quotes_and_missing_dimensions_are_rejected(self):
        invalid = deepcopy(self.ratings)
        invalid['memory']['candidate_quote'] = 'words never spoken'
        with self.assertRaises(ValueError):
            ev.validate_verdict(invalid, self.row['answer'])
        del invalid['memory']
        with self.assertRaises(ValueError):
            ev.validate_verdict(invalid, self.row['answer'])

    def test_control_detects_an_overly_lenient_all_pass_judge(self):
        row = {**self.row, 'judge': self.ratings}
        result = ev.control_diagnostics([self.case], [row])
        self.assertFalse(result['controls_satisfied'])
        self.assertEqual({r['dimension'] for r in result['missed_defects']}, {'relevance', 'continuity'})
        row = deepcopy(row)
        for dimension in ('relevance', 'continuity'):
            row['judge'][dimension]['verdict'] = 'fail'
        self.assertTrue(ev.control_diagnostics([self.case], [row])['controls_satisfied'])

    def test_reviews_require_exact_output_report_and_attribution(self):
        for changed in ({'report_id': 'old'}, {'output_sha256': 'old'}, {'reviewer': ''}, {'run_id': 'unknown'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                ev.attach_reviews(deepcopy(self.report), [{**self.review, **changed}])
        with self.assertRaises(ValueError):
            ev.attach_reviews(deepcopy(self.report), [self.review, self.review])
        tampered = deepcopy(self.report)
        tampered['cases'][0]['answer'] = 'changed answer'
        with self.assertRaises(ValueError):
            ev.attach_reviews(tampered, [self.review])

    def test_calibration_reports_false_passes_separately_from_human_scores(self):
        self.row['judge'] = deepcopy(self.ratings)
        self.review['ratings']['continuity']['verdict'] = 'fail'
        report = ev.attach_reviews(self.report, [self.review])
        self.assertEqual(report['metrics']['calibration']['false_passes'], 1)
        self.assertEqual(report['metrics']['human']['continuity']['fail'], 1)
        self.assertEqual(report['metrics']['judge']['continuity']['pass'], 1)

    def test_comparison_requires_matching_conditions_and_preserves_missing_scores(self):
        new = deepcopy(self.report)
        self.assertEqual(ev.compare(self.report, new)['judge']['continuity']['unscored'], 1)
        for key, value in [('dataset_sha256', 'other'), ('rubric_sha256', 'other'),
                           ('judge_model', 'other'), ('mode', 'offline-fixtures')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                ev.compare(self.report, {**new, key: value})

    def test_comparison_counts_regressions_and_improvements(self):
        old = deepcopy(self.report)
        new = deepcopy(self.report)
        old['cases'][0]['judge'] = deepcopy(self.ratings)
        new['cases'][0]['judge'] = deepcopy(self.ratings)
        old['cases'][0]['judge']['continuity']['verdict'] = 'fail'
        new['cases'][0]['judge']['memory']['verdict'] = 'fail'
        result = ev.compare(old, new)['judge']
        self.assertEqual(result['continuity']['improved'], 1)
        self.assertEqual(result['memory']['regressed'], 1)

    def test_replay_uses_exact_history_and_real_turn_endpoint_then_deletes(self):
        seen = []
        def reply(session, text, docs, call, passage, voice=False):
            seen.append((deepcopy(session['turns']), text, voice))
            return self.row['answer'], docs, {}, False
        with patch.dict(os.environ, {'VECTOR_STORE': 'memory', 'API_PROXY_TOKEN': '',
            'REHEARSAL_AGENT_ENABLED': 'false', 'API_REQUESTS_PER_MINUTE': '100000',
            'API_CLIENT_REQUESTS_PER_MINUTE': '100000'}), patch.object(api, 'LIVE', True), \
            patch.object(api, 'rehearse', side_effect=reply), TestClient(api.app) as client:
            before = set(api.sessions)
            row = ev.generate(client, api, self.case)
            self.assertEqual(set(api.sessions), before)
        self.assertEqual(seen, [(self.case['history'], self.case['learner'], True)])
        self.assertEqual(row['answer'], self.row['answer'])
        self.assertTrue(row['retrieved_passages'])

    def test_failed_replay_still_deletes_session(self):
        with patch.dict(os.environ, {'VECTOR_STORE': 'memory', 'API_PROXY_TOKEN': '',
            'REHEARSAL_AGENT_ENABLED': 'false', 'API_REQUESTS_PER_MINUTE': '100000',
            'API_CLIENT_REQUESTS_PER_MINUTE': '100000'}), patch.object(api, 'LIVE', True), \
            patch.object(api, 'rehearse', side_effect=RuntimeError('fictional failure')), TestClient(api.app) as client:
            before = set(api.sessions)
            with self.assertRaises(RuntimeError):
                ev.generate(client, api, self.case)
            self.assertEqual(set(api.sessions), before)


if __name__ == '__main__':
    unittest.main()
