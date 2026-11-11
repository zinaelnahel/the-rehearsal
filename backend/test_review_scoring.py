"""Review must recover missed learner actions without inventing evidence."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main
from backend.live import RoleReply, EvidenceReview, scene_review_schema, bind_review, strict_schema

GOALS=[
 'Clearly say no to helping this weekend without ambiguity.',
 'Express a firm boundary about not being available for last-minute requests or weekend help.',
 'If the family member insists, calmly restate your boundary and suggest discussing help at another agreed time.'
]
REPLIES=[
 'Lo siento, no puedo ayudarte este sábado. Ya tengo otros planes, pero podemos hablar de otra fecha la semana que viene.',
 'Sí, estoy segura. No puedo este fin de semana, pero puedo hablar contigo el martes para ver si puedo ayudarte con algo concreto.'
]

def review_payload():
 return {'review_assessments':{f'goal_{i}':{'action':'personal_action',
  'learner_turn_id':'turn_0' if i==0 else 'turn_1','learner_quote':REPLIES[0] if i==0 else REPLIES[1]}
  for i in range(3)},'feedback':[{'learner_turn_id':'turn_1','suggestion':'',
  'explanation':'You reaffirmed your refusal and offered another agreed time.'}],
  'unanswered':[{'goal_id':'0','question':'Practise refusing weekend help again.'}],
  'phrases':[],'note':'Review.'}

class ReviewScoringTests(unittest.TestCase):
 def test_exact_reported_custom_goals_recover_from_zero_and_survive_reread(self):
  with patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false',
   'API_REQUESTS_PER_MINUTE':'100000','API_CLIENT_REQUESTS_PER_MINUTE':'100000'}),patch.object(main,'LIVE',True),TestClient(main.app) as c:
   def post(path,body=None):
    r=c.post(path,json=body);self.assertEqual(r.status_code,200,r.text);return r.json()
   sid=post('/api/sessions',{'sample':'difficult','language':'Spanish'})['id'];path='/api/sessions/'+sid
   try:
    post(path+'/mission',{'scenario':'difficult','language':'Spanish','feedback_language':'English','external_model_consent':True})
    post(path+'/start',{'goals':GOALS})
    proposal=RoleReply(reply='Entendido.',citations=[],goal_checks=[],answer_checks=[])
    validation=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
    with patch.object(main,'model',side_effect=[proposal,validation]*2):
     for text in REPLIES:result=post(path+'/turn',{'text':text})
    self.assertEqual(sum(g['achieved'] for g in result['goals']),0)
    payload=review_payload()
    schema=scene_review_schema(2,('0','1','2'))
    invalid=review_payload()
    invalid['review_assessments']['goal_2']['learner_quote']='Invented learner evidence'
    with patch.object(main,'model',return_value=schema.model_validate(invalid)):
     self.assertEqual(c.post(path+'/finish').status_code,502)
    self.assertEqual(sum(g['achieved'] for g in main.sessions[sid]['mission']),0)
    self.assertEqual(main.sessions[sid]['phase'],'chat')
    with patch.object(main,'model',return_value=schema.model_validate(payload)) as model:
     review=post(path+'/finish')
     self.assertEqual(sum(g['achieved'] for g in review['goals']),3)
     self.assertTrue(all(g['answer_status']=='not_applicable' for g in review['goals']))
     self.assertEqual(review['goals'][2]['evidence'],REPLIES[1])
     self.assertEqual(review['unanswered'],[])
     self.assertEqual(post(path+'/finish'),review)
     self.assertEqual(model.call_count,1)
    self.assertEqual(post(path+'/resume')['goals'],review['goals'])
   finally:c.delete(path)

 def test_review_requires_exact_learner_evidence_and_preserves_answer_verification(self):
  mission=[main.Goal(id=str(i),text=g).model_dump() for i,g in enumerate(GOALS)]
  mission[0].update(achieved=True,evidence='Earlier validated evidence',answer_status='unknown')
  payload=review_payload()
  payload['review_assessments']['goal_1']['action']='document_question'
  result=scene_review_schema(2,('0','1','2')).model_validate(payload)
  bind_review(result,REPLIES,mission)
  self.assertEqual(mission[0]['answer_status'],'unknown')
  self.assertEqual(mission[0]['evidence'],'Earlier validated evidence')
  self.assertEqual(mission[1]['answer_status'],'unverified')
  self.assertEqual(mission[1]['answer_sources'],[])
  for bad in ('Invented learner quote','Esperaba contar con tu ayuda.'):
   payload=review_payload();payload['review_assessments']['goal_2']['learner_quote']=bad
   with self.subTest(quote=bad),self.assertRaises(main.HTTPException):
    bind_review(scene_review_schema(2,('0','1','2')).model_validate(payload),REPLIES,
     [main.Goal(id=str(i),text=g).model_dump() for i,g in enumerate(GOALS)])

 def test_provider_schema_requires_every_review_goal(self):
  schema=strict_schema(scene_review_schema(2,('0','1','2')))
  self.assertIn('review_assessments',schema['required'])
  definitions=schema['$defs']['ReviewActionAssessments']
  self.assertEqual(definitions['required'],['goal_0','goal_1','goal_2'])

if __name__=='__main__':unittest.main()
