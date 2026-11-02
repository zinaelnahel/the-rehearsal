import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app, sessions
from backend.context import safety_concern


class ContextFeedbackTests(unittest.TestCase):
 def setUp(self):
  self.enterContext(patch.dict(os.environ, {'API_PROXY_TOKEN':''}))
  self.enterContext(patch('backend.main.LIVE', False))
  self.client=self.enterContext(TestClient(app))
  sessions.clear()

 def scene(self, goal='Ask about rent', text='A private conversation.', scenario='apartment'):
  sid=self.client.post('/api/sessions',json={'text':text}).json()['id']
  mission=self.client.post(f'/api/sessions/{sid}/mission',json={'scenario':scenario,'goal':goal,'language':'English','feedback_language':'English'}).json()
  start=self.client.post(f'/api/sessions/{sid}/start',json={'goals':[g['text'] for g in mission['goals']]}).json()
  return sid,mission,start

 def test_feedback_can_change_clear_and_reject_text(self):
  sid,_,start=self.scene()
  response=start['turns'][0]
  url=f'/api/sessions/{sid}/responses/{response["id"]}/feedback'
  for rating,reason in [('up',None),('down','tone'),('down',None)]:
   self.assertEqual(self.client.put(url,json={'rating':rating,'reason':reason}).status_code,200)
   record=sessions[sid]['ratings'][response['id']]
   self.assertEqual(record,{'rating':rating,'reason':reason,'scenario':'apartment','response_id':response['id'],'version':'roleplay-0.6'})
  self.assertEqual(self.client.put(url,json={'rating':'down','text':'private message'}).status_code,422)
  self.assertEqual(self.client.put(url,json={'rating':'up','reason':'tone'}).status_code,400)
  self.assertEqual(self.client.put(url,json={'rating':None}).status_code,200)
  self.assertEqual(sessions[sid]['ratings'],{})
  other,_,_=self.scene()
  self.assertEqual(self.client.put(url.replace(sid,other),json={'rating':'up'}).status_code,404)
  self.client.delete(f'/api/sessions/{sid}')
  self.assertEqual(self.client.put(url,json={'rating':'up'}).status_code,404)

 def test_new_turn_and_retry_have_unique_response_ids(self):
  sid,mission,start=self.scene()
  turn=self.client.post(f'/api/sessions/{sid}/turn',json={'text':'What is the rent?'}).json()['turn']
  self.assertNotEqual(turn['id'],start['turns'][0]['id'])
  self.client.post(f'/api/sessions/{sid}/finish')
  retry=self.client.post(f'/api/sessions/{sid}/retry',json={'goal_id':mission['goals'][0]['id']}).json()
  self.assertNotEqual(retry['turns'][0]['id'],turn['id'])

 def test_whole_dialogue_rating_is_tied_to_finished_scene(self):
  sid,mission,_=self.scene()
  review=self.client.post(f'/api/sessions/{sid}/finish').json()
  repeated=self.client.post(f'/api/sessions/{sid}/finish').json()
  self.assertEqual(review['feedback_id'],repeated['feedback_id'])
  url=f'/api/sessions/{sid}/responses/{review["feedback_id"]}/feedback'
  self.assertEqual(self.client.put(url,json={'rating':'down','reason':'realism'}).status_code,200)
  self.assertEqual(sessions[sid]['ratings'][review['feedback_id']]['version'],'dialogue-0.6')
  self.client.post(f'/api/sessions/{sid}/retry',json={'goal_id':mission['goals'][0]['id']})
  self.assertEqual(self.client.put(url,json={'rating':'up'}).status_code,404)

 def test_informal_rental_questions_do_not_get_generic_acknowledgement(self):
  sid,_,_=self.scene(text='The monthly rent is 850 euros.')
  for question in ['do i need a work contract', 'do i need a work contract to rent this flat']:
   result=self.client.post(f'/api/sessions/{sid}/turn',json={'text':question}).json()
   self.assertIn('cannot confirm that a work contract is required',result['turn']['content'])
   self.assertEqual(result['turn']['sources'],[])
   self.assertFalse(any(g['achieved'] for g in result['goals']))
  unknown=self.client.post(f'/api/sessions/{sid}/turn',json={'text':'can i have a second viewing'}).json()
  self.assertIn('cannot confirm',unknown['turn']['content'])
  review=self.client.post(f'/api/sessions/{sid}/finish').json()
  self.assertIn('What documents or proof of income are required to rent this flat?',review['unanswered'])

 def test_final_breakup_goals_hints_and_review(self):
  sid,mission,start=self.scene('I want a final breakup',scenario='difficult')
  self.assertIn('ending the relationship',mission['goals'][0]['text'])
  self.assertNotIn('shared plans',start['turns'][0]['content'])
  hint=self.client.post(f'/api/sessions/{sid}/hint',json={'kind':'starter'}).json()['text']
  self.assertIn('ending our relationship',hint)
  self.client.post(f'/api/sessions/{sid}/turn',json={'text':'I am ending our relationship. My decision is final.'})
  review=self.client.post(f'/api/sessions/{sid}/finish').json()
  self.assertTrue(review['goals'][0]['achieved'])
  self.assertTrue(any('final' in p for p in review['phrases']))
  self.assertFalse(any('plans change' in p for p in review['phrases']))

 def test_safety_interrupts_without_provider_calls(self):
  for phrase in ['I am afraid of him','He threatened me','Ich habe Angst','Tengo miedo']:
   self.assertTrue(safety_concern(phrase))
  sid,_,_=self.scene(scenario='difficult')
  with patch('backend.main.LIVE',True),patch('backend.main.rehearse') as roleplay,patch('backend.main.model') as model:
   result=self.client.post(f'/api/sessions/{sid}/turn',json={'text':'He threatened me. I am afraid.'}).json()
   self.assertTrue(result['safety'])
   self.assertTrue(result['turn']['safety'])
   self.assertIn('pause',result['turn']['content'])
   self.assertEqual(result['turn']['sources'],[])
   review=self.client.post(f'/api/sessions/{sid}/finish').json()
   self.assertEqual(review['feedback'],[])
   self.assertEqual(review['phrases'],[])
   roleplay.assert_not_called()
   model.assert_not_called()

 def test_safety_in_source_pauses_opening(self):
  _,mission,start=self.scene(text='I am scared. My partner uses threats.',scenario='difficult')
  self.assertTrue(mission['safety'])
  self.assertTrue(start['turns'][0]['safety'])


if __name__=='__main__': unittest.main()
