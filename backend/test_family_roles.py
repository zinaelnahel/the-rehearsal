"""Language/style matrix with deliberately overpermissive model-review doubles."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from backend import main
from backend.live import EvidenceReview,RoleReply
from backend.family_boundary import FAMILY_BOUNDARY, FAMILY_PACING

DATA=json.loads((Path(__file__).resolve().parents[1]/'evaluation/family-role-regressions.json').read_text(encoding='utf-8'))


class FamilyRoleMatrixTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false','API_REQUESTS_PER_MINUTE':'100000'}))
        self.enterContext(patch('backend.main.LIVE',False))
        self.client=self.enterContext(TestClient(main.app))

    def check_language(self,language):
        fixture=DATA['languages'][language]
        review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
        # A real citation must never license the wrong speaker to adopt a line.
        docs=[Document(page_content=fixture['learner_turn'],metadata={'id':'1','source':'Fictional learner practice notes','location':'Section 1'})]
        counts={'reversals_withheld':0,'valid_replies_delivered':0}
        for style in ('Everyday','B1','B2'):
            sid=self.client.post('/api/sessions',json={'sample':'difficult','language':language}).json()['id']
            path='/api/sessions/'+sid
            try:
                mission=self.client.post(path+'/mission',json={'scenario':'difficult','language':language,'feedback_language':language,'level':style}).json()
                self.client.post(path+'/start',json={'goals':[goal['text'] for goal in mission['goals']]})
                for invalid,key in ((True,'invalid_partner_replies'),(False,'valid_partner_replies')):
                    for candidate in fixture[key]:
                        with self.subTest(language=language,style=style,invalid=invalid,reply=candidate):
                            proposal=RoleReply(reply=candidate+' [1]',citations=['1'],goal_checks=[],answer_checks=[])
                            with patch('backend.main.LIVE',True),patch('backend.main.search',return_value=docs),patch('backend.main.model',side_effect=[proposal,review]):
                                result=self.client.post(path+'/turn',json={'text':fixture['learner_turn']})
                            self.assertEqual(result.status_code,200,result.text)
                            turn=result.json()['turn']
                            self.assertEqual(turn['answer_withheld'],invalid)
                            if invalid:
                                self.assertEqual(turn['content'],FAMILY_BOUNDARY[language]['clarify'])
                                self.assertEqual(turn['sources'],[])
                                counts['reversals_withheld']+=1
                            else:
                                self.assertEqual(turn['content'],FAMILY_PACING[language]['accept'])
                                self.assertEqual(turn['sources'],[])
                                counts['valid_replies_delivered']+=1
                            self.assertEqual(main.sessions[sid]['turns'][-2]['content'],fixture['learner_turn'])
                            for goal in result.json()['goals']:
                                if goal['achieved']:
                                    self.assertEqual(goal['evidence'],fixture['learner_turn'])
                                    self.assertEqual(goal['answer_status'],'not_applicable')
                            # These turns include a boundary immediately; no challenge was delivered.
                            self.assertFalse(result.json()['goals'][2]['achieved'])
            finally:
                self.client.delete(path)
        self.assertEqual(counts,{'reversals_withheld':30,'valid_replies_delivered':21})

    def test_english_speaker_ownership_across_styles(self):self.check_language('English')

    def test_german_speaker_ownership_across_styles(self):self.check_language('German')

    def test_spanish_speaker_ownership_across_styles(self):self.check_language('Spanish')
