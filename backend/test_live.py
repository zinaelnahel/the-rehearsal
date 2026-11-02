"""Deterministic contract tests: no provider calls or real credentials."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app,sessions
from backend.live import RoleReply,GoalCheck,AnswerCheck,EvidenceReview,Translation,strict_schema

class LiveTests(unittest.TestCase):
 def setUp(self):
  sessions.clear()
  env=patch.dict(os.environ,{'API_PROXY_TOKEN':''})
  env.start();self.addCleanup(env.stop)
  self.client=self.enterContext(TestClient(app))
  with patch('backend.main.LIVE',False):
   self.sid=self.client.post('/api/sessions',json={'text':'Monthly rent is 1375 euros. Utilities are included.'}).json()['id']
   self.p='/api/sessions/'+self.sid
   self.client.post(self.p+'/mission',json={'scenario':'apartment','language':'English','feedback_language':'English','level':'Everyday'})
   self.client.post(self.p+'/start',json={'goals':['Ask whether utilities are included']})
  mode=patch('backend.main.LIVE',True)
  mode.start();self.addCleanup(mode.stop)

 def proposal(self,**kwargs):
  values=dict(reply='Utilities are included. [1]',citations=['1'],goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='Are utilities included?')],answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote='Utilities are included.')])
  values.update(kwargs)
  return RoleReply(**values)

 def test_custom_goal_requires_exact_quote_and_verified_answer(self):
  review=EvidenceReview(reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[self.proposal(),review]):
   r=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  self.assertEqual(r.status_code,200,r.text)
  goal=r.json()['goals'][0]
  self.assertTrue(goal['achieved'])
  self.assertEqual(goal['evidence'],'Are utilities included?')
  self.assertEqual(goal['answer_status'],'confirmed')
  self.assertEqual(goal['answer_sources'],['1'])

 def test_reject_fabricated_learner_and_source_quotes_without_saving(self):
  bad=[self.proposal(goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='This was never said')]),self.proposal(answer_checks=[AnswerCheck(goal_id='0',status='supported',source_id='1',source_quote='Pets are always allowed.')])]
  for output in bad:
   with patch('backend.main.model',return_value=output):
    r=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
   self.assertEqual(r.status_code,502,r.text)
   self.assertEqual(len(sessions[self.sid]['turns']),1)
   self.assertFalse(sessions[self.sid]['mission'][0]['achieved'])

 def test_withhold_unsupported_reply_without_confirming_answer(self):
  review=EvidenceReview(reply_supported=False,accepted_goal_ids=['0'],verified_answer_goal_ids=[])
  with patch('backend.main.model',side_effect=[self.proposal(reply='Utilities are included and you can have a free garage.'),review]):
   data=self.client.post(self.p+'/turn',json={'text':'Are utilities included?'}).json()
  self.assertNotIn('garage',data['turn']['content'])
  self.assertTrue(data['turn']['answer_withheld'])
  self.assertTrue(data['goals'][0]['achieved'])
  self.assertEqual(data['goals'][0]['answer_status'],'unverified')
  self.assertEqual(data['turn']['sources'],[])

 def test_semantic_review_can_reject_keyword_only_goal_match(self):
  review=EvidenceReview(reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  proposal=self.proposal(goal_checks=[GoalCheck(goal_id='0',achieved=True,learner_quote='I will not ask about utilities')])
  with patch('backend.main.model',side_effect=[proposal,review]):
   data=self.client.post(self.p+'/turn',json={'text':'I will not ask about utilities'}).json()
  self.assertFalse(data['goals'][0]['achieved'])

 def test_translation_uses_supplied_phrase_and_validates_original(self):
  original='Could we arrange a viewing on Thursday?'
  translated=Translation(original=original,translation='Könnten wir am Donnerstag eine Besichtigung vereinbaren?',explanation='A polite request.')
  with patch('backend.main.model',return_value=translated) as mock:
   r=self.client.post(self.p+'/hint',json={'kind':'translation','text':original})
   self.assertEqual(mock.call_args.args[2]['phrase'],original)
  self.assertIn('Donnerstag',r.json()['text'])
  count=len(sessions[self.sid]['hints'])
  with patch('backend.main.model',return_value=translated):
   r=self.client.post(self.p+'/hint',json={'kind':'translation','text':'Different phrase'})
  self.assertEqual(r.status_code,502)
  self.assertEqual(len(sessions[self.sid]['hints']),count)
  self.assertEqual(self.client.post(self.p+'/hint',json={'kind':'translation','text':''}).status_code,400)

 def test_strict_schema_forbids_extra_fields_recursively(self):
  schema=strict_schema(RoleReply)
  self.assertFalse(schema['additionalProperties'])
  self.assertEqual(set(schema['required']),set(schema['properties']))
  self.assertFalse(schema['$defs']['GoalCheck']['additionalProperties'])

 def test_historical_goal_carry_forward_does_not_rewrite_evidence(self):
  first=EvidenceReview(reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[self.proposal(),first]):
   self.client.post(self.p+'/turn',json={'text':'Are utilities included?'})
  historical=self.proposal(reply='What else would you like to ask?',citations=[])
  # Overbroad review IDs cannot create fresh observations after normalization.
  review=EvidenceReview(reply_supported=True,accepted_goal_ids=['0','invented'],verified_answer_goal_ids=['0'])
  with patch('backend.main.model',side_effect=[historical,review]):
   response=self.client.post(self.p+'/turn',json={'text':'Thank you for explaining.'})
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(response.json()['goals'][0]['evidence'],'Are utilities included?')
  self.assertEqual(response.json()['goals'][0]['answer_status'],'confirmed')

 def test_hourly_budget_rejects_before_provider_request(self):
  from backend.main import model,MissionOutput
  from fastapi import HTTPException
  with patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic-not-a-real-key','MODEL_CALLS_PER_HOUR':'0'}),self.assertRaises(HTTPException) as error:
   model(MissionOutput,'No network call should happen.',{})
  self.assertEqual(error.exception.status_code,429)

 def test_old_demo_client_cannot_start_live_mission_without_notice(self):
  sid=self.client.post('/api/sessions',json={'text':'Fictional advert.'}).json()['id']
  with patch('backend.main.model') as call:
   response=self.client.post('/api/sessions/'+sid+'/mission',json={'scenario':'apartment'})
  self.assertEqual(response.status_code,409)
  call.assert_not_called()

if __name__=='__main__': unittest.main()
