import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main,request_deadline
from backend.live import RoleReply,EvidenceReview

class TurnRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','REHEARSAL_AGENT_ENABLED':'false',
   'API_REQUESTS_PER_MINUTE':'100000','API_CLIENT_REQUESTS_PER_MINUTE':'100000'}))
  self.enterContext(patch.object(main,'LIVE',False))
  self.client=self.enterContext(TestClient(main.app))
  sid=self.client.post('/api/sessions',json={'text':'Monthly rent is 850 euros. Gas and water are included.'}).json()['id']
  self.path='/api/sessions/'+sid;self.session=main.sessions[sid]
  self.client.post(self.path+'/mission',json={'scenario':'apartment','language':'English','feedback_language':'English'})
  self.client.post(self.path+'/start',json={'goals':['Ask about rent']})
 def test_repeated_request_is_returned_without_duplicate_turn_or_model_calls(self):
  body={'text':'What is the rent?','request_id':'repeat-1'}
  first=self.client.post(self.path+'/turn',json=body)
  second=self.client.post(self.path+'/turn',json=body)
  self.assertEqual(first.status_code,200,first.text)
  self.assertEqual(first.json(),second.json())
  self.assertEqual(len(self.session['turns']),3)
  self.assertEqual(self.client.post(self.path+'/turn',json={**body,'text':'Different message'}).status_code,409)
  state=self.client.get(self.path+'/state').json()
  self.assertFalse(state['pending']);self.assertEqual(state['completed_request_ids'],['repeat-1'])
  self.assertEqual(state['turns'],self.session['turns'])
 def test_wall_deadline_discards_late_work_and_unlocks_the_session(self):
  def slow(*args,**kwargs):
   time.sleep(.08)
   return 'Late answer',[],{},False
  with patch.object(main,'LIVE',True),patch.object(main,'rehearse',side_effect=slow),patch.object(request_deadline,'TURN_SECONDS',.02):
   response=self.client.post(self.path+'/turn',json={'text':'What is the rent?','request_id':'slow'})
  self.assertEqual(response.status_code,504,response.text)
  time.sleep(.1)
  self.assertEqual(len(self.session['turns']),1)
  self.assertFalse(self.session['lock'].locked())
  self.assertNotIn('slow',self.session.get('turn_results',{}))
  self.assertEqual(self.client.post(self.path+'/turn',json={'text':'What is the rent?','request_id':'slow'}).status_code,200)
 def test_optional_planner_failure_keeps_required_grounding_checks(self):
  proposal=RoleReply(reply='I do not have that confirmed.',citations=[],goal_checks=[],answer_checks=[])
  review=EvidenceReview(partner_role_consistent=True,reply_supported=True,accepted_goal_ids=[],verified_answer_goal_ids=[])
  with patch.object(main,'LIVE',True),patch.object(main,'agent_enabled',return_value=True),patch.object(main,'prepare_agent',side_effect=main.HTTPException(504,'Planner timeout')),patch.object(main,'model',side_effect=[proposal,review]) as model:
   response=self.client.post(self.path+'/turn',json={'text':'What is the rent?','request_id':'planner'})
  self.assertEqual(response.status_code,200,response.text);self.assertEqual(model.call_count,2)
 def test_provider_timeout_uses_remaining_shared_allowance(self):
  token=request_deadline.deadline.set(time.monotonic()+.1)
  try:self.assertLessEqual(request_deadline.provider_timeout(20),.1)
  finally:request_deadline.deadline.reset(token)
 def test_concurrent_retries_share_one_committed_result(self):
  def slow(*args,**kwargs):
   time.sleep(.04)
   return 'I can answer your question.',[],{},False
  body={'text':'What is the rent?','request_id':'concurrent'}
  with patch.object(main,'LIVE',True),patch.object(main,'rehearse',side_effect=slow) as rehearse,ThreadPoolExecutor(max_workers=2) as workers:
   responses=list(workers.map(lambda _:self.client.post(self.path+'/turn',json=body),range(2)))
  self.assertEqual([r.status_code for r in responses],[200,200])
  self.assertEqual(responses[0].json(),responses[1].json())
  self.assertEqual(rehearse.call_count,1)
  self.assertEqual(len(self.session['turns']),3)

if __name__=='__main__':unittest.main()
