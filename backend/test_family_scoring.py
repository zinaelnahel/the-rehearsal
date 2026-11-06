import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main
from backend.family_boundary import FAMILY_BOUNDARY,FAMILY_PACING,family_action_observations
from backend.live import RoleReply,EvidenceReview,DebriefNotes


class FamilyScoringTests(unittest.TestCase):
    def test_refusal_boundary_and_reaffirmation_survive_model_undercount(self):
        examples=[
            ('Spanish','Este fin de semana no puedo ayudar.','No me lo vuelvas a pedir. Pregúntame antes de contar con mi tiempo.'),
            ('German','Leider kann ich dieses Wochenende nicht helfen.','Bitte frag mich nie wieder. Frag mich vorher, bevor du meine Zeit verplanst.'),
            ('English',"I cannot help this weekend.",'Please never ask me again. Ask me before making plans involving my time.')]
        for language,first,second in examples:
            for feedback_language in ('English','German','Spanish'):
                with self.subTest(language=language,feedback_language=feedback_language),patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false','API_REQUESTS_PER_MINUTE':'100000'}),patch('backend.main.LIVE',True),TestClient(main.app) as client:
                    sid=client.post('/api/sessions',json={'sample':'difficult','language':language}).json()['id']
                    path='/api/sessions/'+sid
                    try:
                        with patch('backend.main.model') as model:
                            response=client.post(path+'/mission',json={'scenario':'difficult','language':language,'feedback_language':feedback_language,'external_model_consent':True})
                            self.assertEqual(response.status_code,200,response.text)
                            model.assert_not_called()
                        goals=[goal['text'] for goal in response.json()['goals']]
                        self.assertEqual(goals,FAMILY_BOUNDARY[feedback_language]['goals'])
                        client.post(path+'/start',json={'goals':goals})
                        proposal=RoleReply(reply='Okay.',citations=[],goal_checks=[],answer_checks=[])
                        review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
                        with patch('backend.main.model',side_effect=[proposal,review,proposal,review]):
                            first_result=client.post(path+'/turn',json={'text':first}).json()
                            self.assertEqual([goal['achieved'] for goal in first_result['goals']],[True,False,False])
                            self.assertEqual(first_result['turn']['content'],FAMILY_PACING[language]['gentle_followup'])
                            second_result=client.post(path+'/turn',json={'text':second}).json()
                        self.assertEqual([goal['achieved'] for goal in second_result['goals']],[True,True,True])
                        self.assertEqual(second_result['goals'][0]['evidence'],first)
                        self.assertEqual(second_result['goals'][1]['evidence'],second)
                        self.assertEqual(second_result['goals'][2]['evidence'],second)
                        self.assertTrue(all(goal['answer_status']=='not_applicable' for goal in second_result['goals']))
                        notes=DebriefNotes(feedback=[{'quote':second,'suggestion':'','explanation':'Clear boundary.'}],unanswered=[],phrases=[],note='Practice review.')
                        with patch('backend.main.model',return_value=notes):
                            debrief=client.post(path+'/finish').json()
                        self.assertEqual(sum(goal['achieved'] for goal in debrief['goals']),3)
                    finally:client.delete(path)

    def test_only_real_actions_on_unchanged_standard_goals_get_extra_credit(self):
        cases=[('Spanish','No puedo ayudar.','No me lo vuelvas a pedir. Pregúntame antes de contar con mi tiempo.',[
            'Traduce: No puedo ayudar.','¿Cómo digo no puedo ayudar?','Ejemplo: Pregúntame antes de contar con mi tiempo.','No puedo decir que no.','tiempo antes limite',"'No puedo ayudar.'",'Si no puedo ayudar, pregúntame antes.']),
            ('English',"I cannot help.",'Please never ask me again. Ask me before making plans involving my time.',[
            'Translate: I cannot help.','How do I say please ask me before making plans?','I cannot say no.','time boundary refusal',"'I cannot help.'",'If I cannot help, ask me first.']),
            ('German','Ich kann nicht helfen.','Bitte frag mich nie wieder. Frag mich vorher, bevor du meine Zeit verplanst.',[
            'Übersetze: Ich kann nicht helfen.','Wie sage ich bitte frag mich vorher?','Ich kann nicht Nein sagen.','Zeit Grenze vorher',"'Ich kann nicht helfen.'",'Kann ich nicht helfen?'])]
        for language,refusal,boundary,invalid in cases:
            session={'family_boundary':True,'setup':{'language':language,'feedback_language':'English'},'mission':[{'id':str(i),'text':text} for i,text in enumerate(FAMILY_BOUNDARY['English']['goals'])],'turns':[]}
            self.assertNotIn('2',family_action_observations(session,boundary))
            session['turns']=[{'role':'user','content':refusal},{'role':'assistant','content':FAMILY_PACING[language]['gentle_followup']}]
            self.assertIn('2',family_action_observations(session,boundary))
            for text in invalid:
                with self.subTest(language=language,text=text):self.assertEqual(family_action_observations(session,text),{})
            session['mission']=[{'id':'custom','text':'Offer to help with errands this weekend'}]
            self.assertEqual(family_action_observations(session,boundary),{})
            session['mission']=[{'id':'0','text':FAMILY_BOUNDARY['English']['goals'][0]}]
            session['breakup']=True
            self.assertEqual(family_action_observations(session,refusal),{})
