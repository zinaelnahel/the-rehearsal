import unittest
from langchain_core.documents import Document
from backend.source_grounding import unsupported_rental_claim
from backend.job_context import mixed_job_answer


class SubmissionRetest(unittest.TestCase):
    def test_future_followup_offers_are_blocked_without_trusting_reviewer(self):
        for reply in (
            'Would you like me to inform you when I know?',
            "I don't know yet, but I can let you know.",
            '¿Quieres que te avise cuando lo sepa?',
            'Ich kann dich informieren, wenn ich es weiß.',
        ):
            with self.subTest(reply=reply):
                self.assertTrue(unsupported_rental_claim(reply, [], []))
        self.assertFalse(unsupported_rental_claim('I do not have a confirmed date yet.', [], []))

    def test_compound_job_recovery_includes_benefits_with_evidence(self):
        doc = Document(page_content='Remote, DE | München\nYour benefits\n- Pension scheme and health management\n- Staff discounts\nApply now', metadata={'id': '1'})
        session = {'setup': {'language': 'English'}, 'source_documents': [doc], 'source_chunks': {'1': doc}}
        text, cited = mixed_job_answer(session, 'What are the remote work arrangements, salary and benefits?', [doc])
        self.assertIn('Remote, DE | München', text)
        self.assertIn('confirmed salary', text)
        self.assertIn('Pension scheme and health management', text)
        self.assertIn('Staff discounts', text)
        self.assertNotIn('Apply now', text)
        self.assertEqual(cited, [doc])

    def test_unavailable_benefit_evidence_stays_unknown(self):
        doc = Document(page_content='Remote, DE | München', metadata={'id': '1'})
        session = {'setup': {'language': 'English'}, 'source_chunks': {'1': doc}}
        text, _ = mixed_job_answer(session, 'What are the remote work arrangements, salary and benefits?', [doc])
        self.assertIn('confirmed benefits details', text)
