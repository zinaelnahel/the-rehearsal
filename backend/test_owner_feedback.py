import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import main,feedback

class OwnerFeedbackTests(unittest.TestCase):
 def setUp(self):
  folder=self.enterContext(tempfile.TemporaryDirectory(prefix='owner-feedback-'))
  self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','FEEDBACK_DB_PATH':str(Path(folder)/'ratings.sqlite3'),'FEEDBACK_OWNER_TOKEN':'x'*40}))
  self.client=self.enterContext(TestClient(main.app))
 def test_unauthorised_requests_never_read_feedback(self):
  with patch('backend.owner_feedback.feedback.report') as report:
   for headers in ({},{'x-feedback-owner-token':'wrong'}):
    response=self.client.get('/api/owner/feedback',headers=headers)
    self.assertEqual(response.status_code,401)
   report.assert_not_called()
 def test_owner_gets_aggregates_only_and_private_cache_headers(self):
  row={key:'' for key in feedback.FIELDS}
  row.update({key:0 for key in feedback.NUMERIC})
  row.update(rating='up',reason='',kind='dialogue',scenario='difficult',language='Spanish',style='B2',mode='live',model='synthetic-test',frontend_build='test',backend_build='test',response_version='test',quality=json.dumps({'relevance':'pass','memory':'uncertain','grounding':'fail'}))
  feedback.save(None,row)
  response=self.client.get('/api/owner/feedback?days=30',headers={'x-feedback-owner-token':'x'*40})
  self.assertEqual(response.status_code,200,response.text)
  data=response.json();self.assertEqual(data['all_ratings']['ratings'],1)
  self.assertEqual(data['quality_ratings']['relevance']['pass'],1)
  self.assertEqual(data['quality_ratings']['memory']['uncertain'],1)
  self.assertEqual(data['quality_ratings']['grounding']['fail'],1)
  self.assertEqual(data['storage'],'temporary')
  self.assertEqual(response.headers['cache-control'],'no-store')
  self.assertNotIn('rows',data);self.assertNotIn('id',data)
  self.assertEqual(self.client.get('/api/owner/feedback?days=366',headers={'x-feedback-owner-token':'x'*40}).status_code,422)
 def test_missing_or_short_owner_secret_fails_closed(self):
  for secret in ('','short'):
   with patch.dict(os.environ,{'FEEDBACK_OWNER_TOKEN':secret}):
    self.assertEqual(self.client.get('/api/owner/feedback',headers={'x-feedback-owner-token':secret}).status_code,503)
 def test_global_backend_proxy_token_is_still_required(self):
  with patch.dict(os.environ,{'API_PROXY_TOKEN':'proxy-test'}):
   self.assertEqual(self.client.get('/api/owner/feedback',headers={'x-feedback-owner-token':'x'*40}).status_code,401)

if __name__=='__main__':unittest.main()
