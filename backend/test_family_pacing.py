import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main
from backend.family_boundary import FAMILY_PACING,family_response_stage
from backend.live import RoleReply,EvidenceReview


class FamilyPacingTests(unittest.TestCase):
    def test_one_followup_then_acceptance_in_demo_and_live(self):
        variants=[('English','no i cant','ok and please never ask me again'),
                  ('German','Leider kann ich nicht.','Bitte frag mich nie wieder.'),
                  ('Spanish','No puedo ayudar.','No me preguntes más.')]
        for live in (False,True):
            for language,soft,firm in variants:
                with self.subTest(language=language,live=live),patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false','API_REQUESTS_PER_MINUTE':'100000'}),patch('backend.main.LIVE',False),TestClient(main.app) as client:
                    sid=client.post('/api/sessions',json={'sample':'difficult','language':language}).json()['id']
                    path='/api/sessions/'+sid
                    mission=client.post(path+'/mission',json={'scenario':'difficult','language':language,'feedback_language':language}).json()
                    client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]})
                    # A model accepting too soon must not eliminate the practice opportunity.
                    proposal=RoleReply(reply='Okay.',citations=[],goal_checks=[],answer_checks=[])
                    review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
                    with patch('backend.main.LIVE',live),patch('backend.main.model',side_effect=[proposal,review]*3):
                        for text,stage in ((soft,'gentle_followup'),(firm,'accept'),(soft,'accept')):
                            response=client.post(path+'/turn',json={'text':text})
                            self.assertEqual(response.status_code,200,response.text)
                            turn=response.json()['turn']
                            self.assertEqual(turn['content'],FAMILY_PACING[language][stage])
                            self.assertEqual(turn['sources'],[])
                            self.assertFalse(turn['answer_withheld'])
                    client.delete(path)

    def test_firm_boundary_immediately_skips_followup_and_questions_do_not_trigger_it(self):
        cases=[('English','Please never ask me again.','What kind of errands?'),
               ('German','Bitte frag mich nicht mehr.','Was für Besorgungen?'),
               ('Spanish','No me vuelvas a preguntar.','¿Qué recados necesitas?')]
        for language,firm,question in cases:
            session={'setup':{'language':language},'turns':[]}
            self.assertEqual(family_response_stage(session,firm),'accept')
            self.assertEqual(family_response_stage(session,question),'natural')
            session['turns']=[{'role':'user','content':firm}]
            self.assertEqual(family_response_stage(session,question),'natural')
