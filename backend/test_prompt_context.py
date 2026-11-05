"""Prompt savings must preserve dialogue and the authoritative evidence set."""
import json
import unittest
from copy import deepcopy

from backend.prompt_context import dialogue_history
from backend.live import rehearse, RoleReply, EvidenceReview
from langchain_core.documents import Document


class PromptContextTests(unittest.TestCase):
    def test_projection_preserves_text_and_session_without_repeated_sources(self):
        turns = [{'role': 'user', 'content': 'Are pets allowed?'},
                 {'role': 'assistant', 'content': 'Not specified. [1]',
                  'sources': [{'id': '1', 'text': 'The pet policy is not specified. ' * 20}],
                  'id': 'response-1', 'answer_withheld': False}]
        original = deepcopy(turns)
        projected = dialogue_history(turns, 16)
        self.assertEqual(projected, [{'role': t['role'], 'content': t['content']} for t in turns])
        self.assertEqual(turns, original)
        self.assertLess(len(json.dumps(projected)), len(json.dumps(turns)))
        self.assertEqual(dialogue_history(turns, 1), projected[-1:])
        self.assertEqual(dialogue_history(turns, None), projected)

    def test_generation_and_independent_review_keep_full_current_evidence(self):
        doc = Document(page_content='Pets are not allowed. Exceptions are not offered.',
                       metadata={'id': '1'})
        session = {'setup': {'scenario': 'apartment', 'language': 'English', 'level': 'Everyday'},
                   'mission': [], 'turns': [{'role': 'assistant', 'content': 'Hello.',
                                            'sources': [{'text': 'obsolete source'}]}]}
        payloads = []

        def call(schema, system, data, session=None):
            payloads.append(deepcopy(data))
            if schema is EvidenceReview:
                return EvidenceReview(partner_role_consistent=True,reply_supported=True, accepted_goal_ids=[], verified_answer_goal_ids=[])
            return RoleReply(reply='Pets are not allowed. [1]', citations=['1'],
                             goal_checks=[], answer_checks=[])

        def passage(d):
            return {'id': d.metadata['id'], 'text': d.page_content}

        reply, cited, _, withheld = rehearse(session, 'Are pets allowed?', [doc], call, passage)
        self.assertFalse(withheld)
        self.assertEqual(cited, [doc])
        self.assertEqual(len(payloads), 2)
        for payload in payloads:
            self.assertEqual(payload['retrieved_passages'], [passage(doc)])
            self.assertEqual(payload['conversation_history'], [{'role': 'assistant', 'content': 'Hello.'}])
        self.assertIn('sources', session['turns'][0])
