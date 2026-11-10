"""OCR protocol and review gate; native recognition also runs in Linux CI."""
import ctypes.util
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from backend import main as api
from backend.parser_process import parse_document


def result(data):return SimpleNamespace(returncode=0,stdout=json.dumps(data).encode())


class OcrTests(unittest.TestCase):
 def test_ocr_fallback_is_bounded_and_does_not_receive_provider_keys(self):
  first=result({'documents':[{'location':'Page 1','text':'','needs_ocr':True}]})
  second=result({'documents':[{'page':0,'text':'Rent is 2400 euros.'}]})
  with patch.dict(os.environ,{'OPENAI_API_KEY':'never-forward-this','API_PROXY_TOKEN':'never-forward-this'}),patch('backend.parser_process.subprocess.run',side_effect=[first,second]) as run:
   docs=parse_document(b'%PDF-fixture','pdf','scan.pdf')
  self.assertEqual(docs[0].page_content,'Rent is 2400 euros.')
  self.assertTrue(docs[0].metadata['ocr'])
  self.assertIn('backend.ocr_parser',run.call_args_list[1].args[0])
  self.assertEqual(run.call_args_list[1].kwargs['timeout'],38)
  for call in run.call_args_list:
   self.assertNotIn('OPENAI_API_KEY',call.kwargs['env'])
   self.assertNotIn('API_PROXY_TOKEN',call.kwargs['env'])

 def test_ocr_limits_and_missing_pages_do_not_silently_import_partial_text(self):
  first=result({'documents':[{'location':'Page '+str(i+1),'text':'','needs_ocr':True} for i in range(9)]})
  with patch('backend.parser_process.subprocess.run',return_value=first) as run:
   with self.assertRaisesRegex(ValueError,'up to 8'):parse_document(b'%PDF-fixture','pdf','scan.pdf')
   self.assertEqual(run.call_count,1)
  first=result({'documents':[{'location':'Page 1','text':'','needs_ocr':True}]})
  with patch('backend.parser_process.subprocess.run',side_effect=[first,result({'documents':[]})]):
   with self.assertRaisesRegex(ValueError,'all requested pages'):parse_document(b'%PDF-fixture','pdf','scan.pdf')

 def test_ocr_source_must_be_reviewed_before_any_mission_model_call(self):
  with patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory','API_REQUESTS_PER_MINUTE':'100000','API_CLIENT_REQUESTS_PER_MINUTE':'100000'}),patch.object(api,'LIVE',False),TestClient(api.app) as client:
   api.sessions.clear()
   pages=[Document(page_content='',metadata={'source':'scan.pdf','location':'Page 1','ocr':True}),
    Document(page_content='Rent is 2,40O euros.',metadata={'source':'scan.pdf','location':'Page 2','ocr':True})]
   with patch.object(api,'parse_document',return_value=pages):
    response=client.post('/api/upload',files={'file':('scan.pdf',b'%PDF-fixture','application/pdf')})
   self.assertEqual(response.status_code,200,response.text)
   data=response.json();self.assertTrue(data['requires_confirmation']);sid=data['id']
   with patch.object(api,'model') as model:
    response=client.post('/api/sessions/'+sid+'/mission',json={'scenario':'apartment','external_model_consent':True})
    self.assertEqual(response.status_code,409,response.text);model.assert_not_called()
   path='/api/sessions/'+sid+'/source-review'
   self.assertEqual(client.post(path,json={'texts':['','Rent is 2400 euros.']}).status_code,409)
   self.assertEqual(client.post(path,json={'texts':['Rent is 2400 euros.'],'confirmed':True}).status_code,400)
   response=client.post(path,json={'texts':['','Rent is 2400 euros.'],'confirmed':True})
   self.assertEqual(response.status_code,200,response.text)
   reviewed=response.json();self.assertFalse(reviewed.get('requires_confirmation',False))
   self.assertEqual(reviewed['import_method'],'reviewed_pdf_ocr')
   self.assertEqual(client.get('/api/sessions/'+sid+'/status').status_code,404)
   focus=client.get('/api/sessions/'+reviewed['id']+'/source/1').json()
   self.assertEqual(focus['page'],2)
   self.assertIn('reviewed OCR text',focus['focus']['location'])
   self.assertEqual(focus['focus']['text'],'Rent is 2400 euros.')
   client.delete('/api/sessions/'+reviewed['id'])
   self.assertEqual(client.get('/api/sessions/'+reviewed['id']+'/source/1').status_code,404)

 @unittest.skipUnless(sys.platform=='linux' and ctypes.util.find_library('tesseract'),'Native OCR runs in Linux CI and the production container')
 def test_real_image_pdf_is_recognised_without_text_layer(self):
  from backend.sandbox_probe import make_scanned_pdf
  docs=parse_document(make_scanned_pdf(),'pdf','synthetic-scan.pdf')
  self.assertTrue(docs[0].metadata['ocr'])
  self.assertIn('2400',docs[0].page_content)
  self.assertIn('2026',docs[0].page_content)
