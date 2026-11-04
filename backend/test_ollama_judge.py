import unittest
from unittest.mock import patch
import httpx
from scripts.judge_quality_ollama import evaluate, judge, local_url
from backend.test_quality_evaluation import row


class OllamaJudgeTests(unittest.TestCase):
 def fixture(self):
  return {'judge_model':'api-model','cases':[row(document='Rent is 1375 euros.',
          question='What is the rent?',goal='Ask about rent',reference='1375 euros',
          judge={'grounding':'supported','answer_correct':True,'goal_correct':True,'explanation':'Exact fact.'})]}

 def test_local_schema_request_and_no_openai_calls(self):
  def handler(request):
   import json
   payload=json.loads(request.content)
   self.assertFalse(payload['stream'])
   self.assertIn('grounding',payload['format']['properties'])
   self.assertEqual(payload['options']['temperature'],0)
   self.assertIn('Rent is 1375 euros.',payload['messages'][1]['content'])
   return httpx.Response(200,json={'done':True,'done_reason':'stop','message':{'content':json.dumps({
      'grounding':'supported','answer_correct':True,'goal_correct':True,'explanation':'Source supports the number.'})}})
  report=self.fixture()
  with httpx.Client(base_url='http://127.0.0.1:11434',transport=httpx.MockTransport(handler)) as client,patch('backend.main.model') as provider:
   result=evaluate(report,client,'local-model')
   provider.assert_not_called()
  self.assertEqual(result['judge_comparison']['grounding_agreement']['rate'],1)
  self.assertEqual(result['additional_openai_calls'],0)
  self.assertEqual(report['cases'][0]['judge']['explanation'],'Exact fact.')

 def test_invalid_or_incomplete_output_never_reuses_previous_pass(self):
  for data in ({'done':False,'message':{'content':'{}'}},
               {'done':True,'done_reason':'length','message':{'content':'{}'}},
               {'done':True,'message':{'content':'not JSON'}}):
   with httpx.Client(base_url='http://127.0.0.1',transport=httpx.MockTransport(lambda request:httpx.Response(200,json=data))) as client:
    result=evaluate(self.fixture(),client,'local-model')
   self.assertIsNone(result['cases'][0]['judge'])
   self.assertIn('judge_error_type',result['cases'][0])
   self.assertIsNone(result['metrics']['judge_unsupported_answer_rate']['rate'])

 def test_only_loopback_endpoint_allowed(self):
  self.assertEqual(local_url('http://localhost:11434/'),'http://localhost:11434')
  for url in ('https://ollama.com','http://example.com','http://user:password@localhost:11434','http://localhost:11434/path'):
   with self.assertRaises(ValueError):local_url(url)
