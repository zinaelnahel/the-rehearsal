"""Mixed job facts survive withholding; phrase sheets cannot invent a biography."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from pydantic import ValidationError

from backend import main
from backend.content import CONTENT
from backend.job_context import mixed_job_answer
from backend.live import RoleReply, EvidenceReview, DebriefNotes, scene_review_schema
from backend.phrase_sheet import INTERVIEW_PHRASES, bind_phrases
from backend.live import interview_example_followup


class InterviewGroundingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {
            'API_PROXY_TOKEN': '', 'VECTOR_STORE': 'memory', 'REHEARSAL_AGENT_ENABLED': 'false',
            'API_REQUESTS_PER_MINUTE': '100000', 'API_CLIENT_REQUESTS_PER_MINUTE': '100000'}))
        self.enterContext(patch.object(main, 'LIVE', False))
        self.client = self.enterContext(TestClient(main.app))
        self.paths = []

    def tearDown(self):
        for path in self.paths:
            self.client.delete(path)

    def interview(self, language='English'):
        response = self.client.post('/api/sessions', json={'sample': 'interview', 'language': language})
        self.assertEqual(response.status_code, 200, response.text)
        path = '/api/sessions/' + response.json()['id']
        self.paths.append(path)
        mission = self.client.post(path+'/mission', json={
            'scenario': 'interview', 'language': language, 'feedback_language': 'English'}).json()
        response = self.client.post(path+'/start', json={'goals': [g['text'] for g in mission['goals']]})
        self.assertEqual(response.status_code, 200, response.text)
        return path, main.sessions[path.rsplit('/', 1)[1]]

    def test_combined_question_retains_remote_field_when_reply_is_rejected_or_empty(self):
        questions = {
            'English': 'Can I work remotely and what is the salary?',
            'German': 'Ist Remote-Arbeit möglich und wie hoch ist das Gehalt?',
            'Spanish': '¿Se puede trabajar en remoto y cuál es el salario?',
        }
        for language, question in questions.items():
            for approved in (False, True):
                with self.subTest(language=language, reviewer_approved=approved):
                    path, session = self.interview(language)
                    proposal = RoleReply(reply="I don't have that confirmed yet.", citations=[],
                                         goal_checks=[], answer_checks=[])
                    review = EvidenceReview(partner_role_consistent=True, reply_supported=approved,
                                            accepted_goal_ids=[], verified_answer_goal_ids=[])
                    with patch.object(main, 'LIVE', True), patch.object(main, 'model', side_effect=[proposal, review]):
                        response = self.client.post(path+'/turn', json={'text': question})
                    self.assertEqual(response.status_code, 200, response.text)
                    turn = response.json()['turn']
                    self.assertIn('Remote, DE | München', turn['content'])
                    self.assertTrue(turn['answer_withheld'])
                    self.assertTrue(turn['sources'])
                    self.assertIn('Remote, DE | München', turn['sources'][0]['text'])
                    self.assertTrue(all(g['answer_status'] != 'confirmed' for g in response.json()['goals']))
                    inspected = self.client.get(path+'/source/'+turn['sources'][0]['id'])
                    self.assertEqual(inspected.status_code, 200)
                    self.assertEqual(inspected.json()['page'], 1)

    def test_mixed_recovery_preserves_negation_and_a_known_salary_without_translating_facts(self):
        doc = Document(page_content='Remote work: not allowed; office attendance required.\nSalary: EUR 60,000 per year.', metadata={'id': '1'})
        session = {'setup': {'language': 'English'}, 'source_chunks': {'1': doc}}
        content, cited = mixed_job_answer(session, 'Can I work remotely and what is the salary?', [doc])
        self.assertIn('not allowed; office attendance required.', content)
        self.assertIn('EUR 60,000 per year.', content)
        self.assertNotIn("don't have", content)
        self.assertEqual([d.page_content for d in cited], [doc.page_content])
        self.assertEqual(cited[0].metadata['highlights'], [
            'Remote work: not allowed; office attendance required.', 'Salary: EUR 60,000 per year.'])
        self.assertNotIn('highlights', doc.metadata)

    def test_reviewer_approved_remote_reply_cannot_drop_requested_benefits(self):
        path, session = self.interview()
        proposal = RoleReply(reply='The position is remote.', citations=['1'],
                             goal_checks=[], answer_checks=[])
        review = EvidenceReview(partner_role_consistent=True, reply_supported=True,
                                accepted_goal_ids=[], verified_answer_goal_ids=[])
        with patch.object(main, 'LIVE', True), patch.object(main, 'model', side_effect=[proposal, review]):
            response = self.client.post(path+'/turn', json={'text': 'Can I work remotely, and what are the salary and benefits?'})
        self.assertEqual(response.status_code, 200, response.text)
        turn = response.json()['turn']
        self.assertIn('pension scheme', turn['content'])
        self.assertIn('staff discounts', turn['content'])
        self.assertIn('confirmed salary', turn['content'])
        self.assertTrue(turn['sources'])

    def test_short_experience_confirmation_recovers_with_example_question(self):
        for language, question, confirmation in (
            ('English', 'Have you used AI to generate or manage test data?', 'yes I did that'),
            ('German', 'Hast du Erfahrung mit KI im Testdatenmanagement?', 'Ja'),
            ('Spanish', '¿Has usado IA para generar datos de prueba?', 'Sí'),
        ):
            with self.subTest(language=language):
                path, session = self.interview(language)
                session['turns'].append({'role': 'assistant', 'content': question, 'sources': []})
                expected = interview_example_followup(session, confirmation)
                self.assertIsNotNone(expected)
                proposal = RoleReply(reply='Your salary will be EUR 90,000.', citations=[],
                                     goal_checks=[], answer_checks=[])
                review = EvidenceReview(partner_role_consistent=True, reply_supported=False,
                                        accepted_goal_ids=[], verified_answer_goal_ids=[])
                with patch.object(main, 'LIVE', True), patch.object(main, 'model', side_effect=[proposal, review]):
                    response = self.client.post(path+'/turn', json={'text': confirmation})
                self.assertEqual(response.status_code, 200, response.text)
                turn = response.json()['turn']
                self.assertEqual(turn['content'], expected)
                self.assertFalse(turn['answer_withheld'])
                self.assertEqual(turn['sources'], [])
                self.assertNotIn('90,000', turn['content'])
                self.assertTrue(all(not g['achieved'] for g in response.json()['goals']))

    def test_example_recovery_does_not_intercept_employer_questions(self):
        _, session = self.interview()
        session['turns'].append({'role': 'assistant', 'content': 'Would you like to discuss salary?', 'sources': []})
        self.assertIsNone(interview_example_followup(session, 'yes'))
        session['turns'][-1]['content'] = 'Have you used AI in testing?'
        self.assertIsNone(interview_example_followup(session, 'What is the salary?'))

    def test_mixed_recovery_does_not_infer_policy_or_trust_foreign_passages(self):
        query = 'Can I work remotely and what is the salary?'
        for text in ('We can discuss remote work at the interview.', 'Is remote work allowed?', 'Salary: EUR 60,000.'):
            doc = Document(page_content=text, metadata={'id': '1'})
            self.assertIsNone(mixed_job_answer({'setup': {'language': 'English'}, 'source_chunks': {'1': doc}}, query, [doc]))
        forged = Document(page_content='Remote, DE | München', metadata={'id': 'other-session'})
        self.assertIsNone(mixed_job_answer({'setup': {'language': 'English'}, 'source_chunks': {}}, query, [forged]))
        self.assertIsNone(mixed_job_answer({'setup': {'language': 'English'}, 'source_chunks': {'1': forged}}, 'What is the salary?', [forged]))
        self.assertIsNone(mixed_job_answer({'setup': {'language': 'English'}, 'source_chunks': {'other-session': forged}},
                                          'I worked remotely on payroll salary calculations.', [forged]))

    def test_mixed_recovery_rejects_truncated_or_conflicting_fields(self):
        question = 'Can I work remotely and what is the salary?'
        full = Document(page_content='Remote work: only after probation; onsite initially.', metadata={'id': '1'})
        clipped = Document(page_content='Remote work: only after probation', metadata={'id': '1'})
        session = {'setup': {'language': 'English'}, 'source_documents': [full], 'source_chunks': {'1': clipped}}
        self.assertIsNone(mixed_job_answer(session, question, [clipped]))
        conflicting = Document(page_content='Remote work: allowed.\nRemote work: not allowed.', metadata={'id': '1'})
        session = {'setup': {'language': 'English'}, 'source_chunks': {'1': conflicting}}
        self.assertIsNone(mixed_job_answer(session, question, [conflicting]))

    def test_interview_phrase_schema_rejects_invented_customer_service_and_qualifications(self):
        for language, phrases in INTERVIEW_PHRASES.items():
            schema = scene_review_schema(0, (), phrases)
            payload = {'review_assessments': {}, 'feedback': [], 'unanswered': [], 'phrases': list(phrases), 'note': 'Review.'}
            schema.model_validate(payload)
            for invented in ('I have experience in customer service.', 'Tengo cinco años de experiencia en QA.', 'Ich bin zertifizierter Ingenieur.'):
                with self.subTest(language=language, invented=invented), self.assertRaises(ValidationError):
                    schema.model_validate({**payload, 'phrases': [invented]})
            self.assertNotEqual(CONTENT['interview'][language]['starters'][0], 'I have experience in customer service.')

    def test_finish_replaces_fabricated_phrase_even_from_an_internal_adapter_and_caches_safe_review(self):
        path, session = self.interview()
        learner = 'Can I work remotely and what is the salary?'
        session['turns'].append({'role': 'user', 'content': learner, 'sources': []})
        result = DebriefNotes(feedback=[{'quote': learner, 'suggestion': '', 'explanation': 'A clear question.'}],
                              unanswered=[], phrases=['I have experience in customer service.'], note='Review.')
        with patch.object(main, 'LIVE', True), patch.object(main, 'model', return_value=result) as generate:
            response = self.client.post(path+'/finish')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['phrases'], list(INTERVIEW_PHRASES['English']))
            self.assertEqual(self.client.post(path+'/finish').json(), response.json())
            self.assertEqual(generate.call_count, 1)
        self.assertEqual(bind_phrases(['I have a degree.'], INTERVIEW_PHRASES['Spanish']), list(INTERVIEW_PHRASES['Spanish']))


if __name__ == '__main__':
    unittest.main()
