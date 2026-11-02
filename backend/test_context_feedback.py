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
   self.assertEqual(record,{'rating':rating,'reason':reason,'scenario':'apartment','response_id':response['id'],'version':'roleplay-0.6.1'})
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

 def test_resume_preserves_turns_and_refreshes_review(self):
  sid,_,_=self.scene(text='The monthly rent is 850 euros.')
  path=f'/api/sessions/{sid}'
  self.assertEqual(self.client.post(path+'/resume').status_code,409)
  self.client.post(path+'/turn',json={'text':'How much is the rent?'})
  original=self.client.post(path+'/finish').json()
  turns=list(sessions[sid]['turns'])
  self.client.put(path+f'/responses/{original["feedback_id"]}/feedback',json={'rating':'up'})
  resumed=self.client.post(path+'/resume')
  self.assertEqual(resumed.status_code,200)
  self.assertEqual(resumed.json()['turns'],turns)
  self.assertEqual(sessions[sid]['ratings'],{})
  self.assertNotIn('debrief',sessions[sid])
  self.assertEqual(self.client.post(path+'/turn',json={'text':'When is it available?'}).status_code,200)
  updated=self.client.post(path+'/finish').json()
  self.assertNotEqual(original['feedback_id'],updated['feedback_id'])
  self.assertEqual(len(sessions[sid]['turns']),len(turns)+2)

 def test_plan_restart_requires_explicit_reset_and_preserves_state_on_cancel(self):
  sid,_,_=self.scene()
  path=f'/api/sessions/{sid}'
  self.client.post(path+'/turn',json={'text':'Do I need a work contract?'})
  original=self.client.post(path+'/finish').json()
  before=list(sessions[sid]['turns'])
  for body in ({'goals':['Ask about rent']},{'goals':['x'],'reset':True}):
   self.assertIn(self.client.post(path+'/start',json=body).status_code,(400,409))
   self.assertEqual(sessions[sid]['turns'],before)
   self.assertEqual(sessions[sid]['debrief'],original)
  restarted=self.client.post(path+'/start',json={'goals':['Ask about the deposit'],'reset':True})
  self.assertEqual(restarted.status_code,200)
  self.assertEqual(len(restarted.json()['turns']),1)
  self.assertEqual(restarted.json()['goals'][0]['text'],'Ask about the deposit')
  self.assertNotIn('debrief',sessions[sid])
  self.assertNotIn('extra_questions',sessions[sid])
  self.assertEqual(sessions[sid]['ratings'],{})

 def test_safety_pause_cannot_resume_ordinary_roleplay(self):
  sid,_,_=self.scene(text='I am afraid of threats.',scenario='difficult')
  path=f'/api/sessions/{sid}'
  self.client.post(path+'/finish')
  self.assertEqual(self.client.post(path+'/resume').status_code,409)
  self.assertEqual(sessions[sid]['phase'],'debrief')

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

 def test_family_sample_keeps_partner_in_role_and_supports_a_clear_no(self):
  sid=self.client.post('/api/sessions',json={'sample':'difficult','language':'English'}).json()['id']
  path=f'/api/sessions/{sid}'
  mission=self.client.post(path+'/mission',json={'scenario':'difficult','language':'English','feedback_language':'English'}).json()
  self.assertFalse(mission['safety'])
  self.assertIn('Say no clearly',mission['goals'][0]['text'])
  opening=self.client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]}).json()['turns'][0]['content']
  self.assertEqual(opening,'Could you help me with errands this weekend?')
  for statement in ["I can't help this weekend.",'Please ask me before making plans that involve my time.',"I understand you're disappointed. My answer is still no."]:
   result=self.client.post(path+'/turn',json={'text':statement}).json()
   self.assertNotIn('What would you like to discuss next',result['turn']['content'])
   self.assertEqual(result['turn']['sources'],[])
  self.assertTrue(all(g['achieved'] for g in result['goals']))
  self.assertTrue(all(g['answer_status']=='not_applicable' for g in result['goals']))
  review=self.client.post(path+'/finish').json()
  self.assertIn("I can't help this weekend.",review['phrases'])
  self.assertFalse(any('plans change' in phrase for phrase in review['phrases']))

 def test_family_sample_does_not_override_custom_context_or_final_breakup(self):
  _,mission,_=self.scene(goal='Raise a concern about work',scenario='difficult')
  self.assertNotIn('weekend',str(mission))
  sid=self.client.post('/api/sessions',json={'sample':'difficult','language':'English'}).json()['id']
  mission=self.client.post(f'/api/sessions/{sid}/mission',json={'scenario':'difficult','goal':'I want a final breakup','language':'English','feedback_language':'English'}).json()
  self.assertIn('ending the relationship',mission['goals'][0]['text'])

 def test_live_family_partner_is_the_requester_not_the_person_saying_no(self):
  from backend.live import RoleReply, EvidenceReview
  sid=self.client.post('/api/sessions',json={'sample':'difficult','language':'English'}).json()['id']
  path=f'/api/sessions/{sid}'
  mission=self.client.post(path+'/mission',json={'scenario':'difficult','language':'English','feedback_language':'English'}).json()
  self.client.post(path+'/start',json={'goals':[g['text'] for g in mission['goals']]})
  reply=RoleReply(reply='I was hoping you could help. Is your answer definite?',citations=[],goal_checks=[],answer_checks=[])
  review=EvidenceReview(reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch('backend.main.LIVE',True),patch('backend.main.model',side_effect=[reply,review]) as model:
   result=self.client.post(path+'/turn',json={'text':"I can't help this weekend."})
   self.assertEqual(result.status_code,200,result.text)
   self.assertIn('You are making the request, NOT the person declining it',model.call_args_list[0].args[1])
   self.assertIn('person declining the family request',model.call_args_list[0].args[2]['learner_role'])

 def test_family_short_no_and_inability_to_say_no_are_distinct(self):
  from backend.family_boundary import family_intents
  for language,no,not_a_refusal in [('English','No',"I can't say no"),('German','Nein','Ich kann nicht Nein sagen'),('Spanish','No','No puedo decir que no')]:
   self.assertIn(0,family_intents(no,language))
   self.assertNotIn(0,family_intents(not_a_refusal,language))

 def test_live_two_letter_no_keeps_exact_evidence_validation(self):
  from backend.live import RoleReply, EvidenceReview
  sid,_,_=self.scene(goal='Say no clearly',scenario='difficult')
  path=f'/api/sessions/{sid}'
  reply=RoleReply(reply='Is that your final answer?',citations=[],goal_checks=[{'goal_id':'0','achieved':True,'learner_quote':'No'}],answer_checks=[{'goal_id':'0','status':'not_document_question','source_id':'','source_quote':''}])
  review=EvidenceReview(reply_supported=True,accepted_goal_ids=['0'],verified_answer_goal_ids=[])
  with patch('backend.main.LIVE',True),patch('backend.main.model',side_effect=[reply,review]):
   result=self.client.post(path+'/turn',json={'text':'No'})
   self.assertEqual(result.status_code,200,result.text)
   self.assertTrue(result.json()['goals'][0]['achieved'])
   self.assertEqual(result.json()['goals'][0]['evidence'],'No')

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
