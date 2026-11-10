"""Source inspection is session-scoped, read-only and preserves page boundaries."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from backend import main as api


class SourceViewTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ,{'API_PROXY_TOKEN':'','VECTOR_STORE':'memory',
            'API_REQUESTS_PER_MINUTE':'100000','API_CLIENT_REQUESTS_PER_MINUTE':'100000'}))
        self.enterContext(patch.object(api,'LIVE',False))
        api.sessions.clear()
        self.client=self.enterContext(TestClient(api.app))

    def test_pdf_citation_opens_full_correct_page_with_exact_focus(self):
        page='Location details. '*70+'The rent is 1200 dollars per month.'
        documents=[Document(page_content='Cover page.',metadata={'source':'flat.pdf','location':'Page 1'}),
            Document(page_content=page,metadata={'source':'flat.pdf','location':'Page 2'})]
        with patch.object(api,'parse_document',return_value=documents):
            response=self.client.post('/api/upload',files={'file':('flat.pdf',b'%PDF-fixture','application/pdf')})
        self.assertEqual(response.status_code,200,response.text)
        sid=response.json()['id']
        focus=next(d for d in api.sessions[sid]['source_chunks'].values() if '1200' in d.page_content)
        response=self.client.get('/api/sessions/'+sid+'/source/'+focus.metadata['id'])
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(data['page'],2)
        self.assertEqual(data['kind'],'pdf')
        self.assertEqual(data['sections'],[{'location':'Page 2','text':page,'selected':True}])
        self.assertEqual(data['focus']['text'],focus.page_content)
        self.assertIn(data['focus']['text'],page)
        self.assertNotIn('Cover page.',str(data))

    def test_text_context_cannot_read_other_sessions_and_disappears_on_delete(self):
        first=self.client.post('/api/sessions',json={'text':'First line.\nRent is 1200 dollars.\nLast line.'}).json()['id']
        second=self.client.post('/api/sessions',json={'text':'Different private source.'}).json()['id']
        response=self.client.get('/api/sessions/'+first+'/source/2')
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertIsNone(data['page'])
        self.assertEqual(data['focus']['text'],'Rent is 1200 dollars.')
        self.assertEqual([s['selected'] for s in data['sections']],[False,True,False])
        own=self.client.get('/api/sessions/'+second+'/source/1').json()
        self.assertNotIn('1200',str(own))
        self.assertEqual(self.client.get('/api/sessions/'+second+'/source/2').status_code,404)
        self.client.delete('/api/sessions/'+first)
        self.assertEqual(self.client.get('/api/sessions/'+first+'/source/2').status_code,404)

    def test_docx_context_uses_paragraphs_without_inventing_pages(self):
        documents=[Document(page_content=text,metadata={'source':'flat.docx','location':'Paragraph '+str(i+1)})
            for i,text in enumerate(['Introduction.','Pets policy is not specified.','Closing notes.'])]
        with patch.object(api,'parse_document',return_value=documents):
            response=self.client.post('/api/upload',files={'file':('flat.docx',b'PK-fixture','application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
        sid=response.json()['id']
        data=self.client.get('/api/sessions/'+sid+'/source/2').json()
        self.assertEqual(data['kind'],'docx')
        self.assertIsNone(data['page'])
        self.assertEqual(data['sections'][1]['location'],'Paragraph 2')
