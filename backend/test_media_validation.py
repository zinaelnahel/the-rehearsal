"""Hostile document inputs exercise the real disposable parser and upload API."""
import io
import os
import unittest
import zipfile
from unittest.mock import patch
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from backend import main as api


class MediaValidationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {'VECTOR_STORE':'memory','API_PROXY_TOKEN':''}))
        self.enterContext(patch.object(api,'LIVE',False))
        api.sessions.clear()
        self.client=self.enterContext(TestClient(api.app))

    def pdf(self, pages=1, encrypted=False):
        writer=PdfWriter()
        for _ in range(pages):writer.add_blank_page(width=100,height=100)
        if encrypted:writer.encrypt('fictional-password')
        out=io.BytesIO();writer.write(out)
        return out.getvalue()

    def test_encrypted_scanned_and_excessive_page_pdfs_create_no_session(self):
        for name,raw in [('encrypted.pdf',self.pdf(encrypted=True)),
                         ('scan.pdf',self.pdf()),('pages.pdf',self.pdf(101)),
                         ('malformed.pdf',b'%PDF-1.7\ncorrupt')]:
            with self.subTest(name=name):
                response=self.client.post('/api/upload',files={'file':(name,raw)})
                self.assertEqual(response.status_code,400,response.text)
                self.assertFalse(api.sessions)

    def test_docx_zip_bomb_and_malformed_xml_create_no_session(self):
        for name,xml in [('expanded.docx',b'x'*(20*1024*1024+1)),
                         ('invalid.docx',b'<broken>')]:
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('word/document.xml',xml)
            response=self.client.post('/api/upload',files={'file':(name,out.getvalue())})
            self.assertEqual(response.status_code,400,response.text)
            self.assertFalse(api.sessions)
