import os
import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main
from backend.family_boundary import FAMILY_BOUNDARY,FAMILY_PACING,family_action_observations
from backend.live import RoleReply,EvidenceReview,DebriefNotes
from backend.sample_sources import SAMPLES


class FamilyScoringTests(unittest.TestCase):
    def test_reported_audio_reaffirmation_agrees_with_live_goals_and_review(self):
        first='No puedo ayudar este fin de semana. Por favor, avísame antes de contar con mi tiempo.'
        second='Sí, estoy segura. No puedo este fin de semana, pero puedo hablar contigo el martes para ver si puedo ayudarte con algo concreto.'
        script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
        transcript='\n'.join(part['speaker']+': '+part['text'] for part in script['turns'])
        for live in (False,True):
            for feedback_language in ('English','German','Spanish'):
                with self.subTest(live=live,feedback_language=feedback_language),patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false','API_REQUESTS_PER_MINUTE':'100000','API_CLIENT_REQUESTS_PER_MINUTE':'100000'}),patch.object(main,'LIVE',live),TestClient(main.app) as client:
                    response=client.post('/api/sessions',json={'sample':'difficult','sample_audio_text':transcript,'transcript_confirmed':True,'language':'Spanish'})
                    self.assertEqual(response.status_code,200,response.text)
                    path='/api/sessions/'+response.json()['id']
                    try:
                        mission=client.post(path+'/mission',json={'scenario':'difficult','language':'Spanish','feedback_language':feedback_language,'external_model_consent':live}).json()
                        client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]})
                        proposal=RoleReply(reply='Entendido.',citations=[],goal_checks=[],answer_checks=[])
                        review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
                        with patch('backend.main.model',side_effect=[proposal,review]*2):
                            before=client.post(path+'/turn',json={'text':first}).json()
                            self.assertEqual([g['achieved'] for g in before['goals']],[True,True,False])
                            self.assertEqual(before['turn']['content'],FAMILY_PACING['Spanish']['gentle_followup'])
                            after=client.post(path+'/turn',json={'text':second}).json()
                        self.assertEqual([g['achieved'] for g in after['goals']],[True,True,True])
                        self.assertEqual(after['goals'][2]['evidence'],second)
                        self.assertEqual(after['goals'][2]['answer_status'],'not_applicable')
                        notes=DebriefNotes(feedback=[{'quote':second,'suggestion':'','explanation':'You reaffirmed the weekend boundary and offered a separate conversation on Tuesday.'}],unanswered=[],phrases=[],note='Practice review.')
                        with patch('backend.main.model',return_value=notes) as model:
                            final=client.post(path+'/finish').json()
                        self.assertEqual(final['goals'],after['goals'])
                        self.assertEqual(sum(g['achieved'] for g in final['goals']),3)
                        if live:
                            self.assertEqual(model.call_args.args[2]['mission'],after['goals'])
                            self.assertEqual(final['feedback'][0]['quote'],second)
                    finally:
                        client.delete(path)

    def test_affirmative_weekend_refusals_and_standard_reaffirmations(self):
        cases=[('Spanish','Sí, estoy segura. No puedo este fin de semana.','Mi respuesta sigue siendo no.'),
               ('Spanish','Sí estoy segura. No puedo ayudar este fin de semana.','Mi respuesta sigue siendo no.'),
               ('English',"Yes, I'm sure. I cannot this weekend.",'My answer is still no.'),
               ('German','Ja, ich bin sicher. Ich kann dieses Wochenende nicht.','Meine Antwort bleibt Nein.')]
        for language,elliptical,reaffirmation in cases:
            session={'family_boundary':True,'setup':{'language':language,'feedback_language':'English'},'mission':[{'id':str(i),'text':goal} for i,goal in enumerate(FAMILY_BOUNDARY['English']['goals'])],'turns':[]}
            for text in (elliptical,reaffirmation):
                with self.subTest(language=language,text=text):
                    self.assertEqual(set(family_action_observations(session,text)),{'0'})
                    session['turns']=[{'role':'assistant','content':FAMILY_PACING[language]['gentle_followup']}]
                    self.assertEqual(set(family_action_observations(session,text)),{'0','2'})
                    session['turns']=[]
        spanish={**session,'setup':{'language':'Spanish','feedback_language':'English'},'turns':[{'role':'assistant','content':FAMILY_PACING['Spanish']['gentle_followup']}]}
        for text in ('Si no puedo este fin de semana, avísame antes.','Sí, puedo hablar contigo el martes.','¿No puedo este fin de semana?'):
            with self.subTest(text=text):
                self.assertEqual(family_action_observations(spanish,text),{})

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
