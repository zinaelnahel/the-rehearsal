"""Evaluation arithmetic must not turn missing labels or failed runs into passes."""
import unittest
from copy import deepcopy
from scripts.evaluate_quality import summarize, rate, digest, attach_reviews


def row(**changes):
    result=dict(id='case',run_id='case:1',category='fact',language='English',answer='1375',
        answer_sha256=digest('1375'),achieved=True,expected_achieved=True,status='confirmed',
        expected_status='confirmed',withheld=False,evidence_rank=1,citation_integrity=True,
        required_value='1375',required_value_present=True,judge=None,human=None)
    return {**result,**changes}


class QualityEvaluationTests(unittest.TestCase):
    def test_empty_denominator_is_not_perfect_score(self):
        self.assertIsNone(rate(0,0)['rate'])
        self.assertIsNone(rate(0,0)['wilson_95_interval'])
        self.assertIsNone(summarize([])['goal_f1'])

    def test_confusion_matrix_and_failed_run_coverage(self):
        rows=[row(),row(expected_achieved=False),row(achieved=False),{'error_type':'TimeoutError'}]
        scores=summarize(rows)
        self.assertEqual(scores['goal_precision']['rate'],.5)
        self.assertEqual(scores['goal_recall']['rate'],.5)
        self.assertEqual(scores['goal_f1'],.5)
        self.assertEqual(scores['completion']['rate'],.75)
        self.assertIsNone(scores['judge_unsupported_answer_rate']['rate'])

    def test_missing_policy_false_confirmation_and_withholding_are_separate(self):
        scores=summarize([row(expected_status='unknown'),row(withheld=True,status='unverified')])
        self.assertEqual(scores['unknown_false_confirmation']['rate'],1)
        self.assertEqual(scores['answerable_withheld']['rate'],1)
        self.assertEqual(scores['answerable_confirmed']['rate'],0)

    def test_judge_uncertainty_is_missing_coverage_not_a_pass(self):
        scores=summarize([row(judge={'grounding':'uncertain'}),row(judge={
            'grounding':'unsupported','answer_correct':False,'goal_correct':True})])
        self.assertEqual(scores['judge_coverage']['rate'],.5)
        self.assertEqual(scores['judge_unsupported_answer_rate']['rate'],1)

    def test_small_zero_error_sample_still_has_nonzero_upper_interval(self):
        self.assertGreater(rate(0,10)['wilson_95_interval'][1],.2)

    def test_human_review_is_bound_to_dataset_answer_and_reviewer(self):
        report={'dataset_sha256':'dataset','cases':[row()]}
        review=dict(run_id='case:1',dataset_sha256='dataset',answer_sha256=digest('1375'),
            reviewer='Reviewer A',grounding='supported',answer_correct=True,goal_correct=True,explanation='Exact value.')
        scored=attach_reviews(deepcopy(report),[review])
        self.assertEqual(scored['metrics']['human_coverage']['rate'],1)
        for changes in ({'answer_sha256':'wrong'},{'dataset_sha256':'wrong'},{'reviewer':''}):
            with self.assertRaises(ValueError):attach_reviews(deepcopy(report),[{**review,**changes}])
        with self.assertRaises(ValueError):attach_reviews(deepcopy(report),[review,review])
