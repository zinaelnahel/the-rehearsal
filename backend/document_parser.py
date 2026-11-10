"""Disposable document parser worker. No provider or application imports."""
import io
import os
from backend.parser_sandbox import confine
import json
import sys
import zipfile
from xml.etree import ElementTree as ET
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_core.document_loaders import BaseLoader

class MemoryLoader(BaseLoader):
 def __init__(self, raw, kind, name): self.raw, self.kind, self.name = raw, kind, name
 def lazy_load(self):
  if self.kind == 'pdf':
   reader = PdfReader(io.BytesIO(self.raw))
   if reader.is_encrypted or len(reader.pages) > 100: raise ValueError('Use an unencrypted PDF with at most 100 pages.')
   for i, page in enumerate(reader.pages):
    text=page.extract_text() or ''
    needs_ocr=(not text.strip() or (len(text.strip())<250 and bool(page.images))) and bool(page.get('/Contents') or page.get('/Annots'))
    yield Document(page_content=text, metadata={'source':self.name,'location':f'Page {i+1}','needs_ocr':needs_ocr})
  elif self.kind == 'docx':
   with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
    if sum(x.file_size for x in z.infolist()) > 20 * 1024 * 1024: raise ValueError('Expanded DOCX is too large.')
    root = ET.fromstring(z.read('word/document.xml'))
    ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    for i, p in enumerate(root.findall('.//w:p', ns)):
     content = ''.join(t.text or '' for t in p.findall('.//w:t',ns))
     if content.strip(): yield Document(page_content=content,metadata={'source':self.name,'location':f'Paragraph {i+1}'})
  else:
   for i, paragraph in enumerate(self.raw.decode('utf-8').splitlines()):
    if paragraph.strip(): yield Document(page_content=paragraph, metadata={'source':self.name,'location':f'Section {i+1}'})


if __name__ == '__main__':
 try:
  if sys.platform == 'linux':
   import resource
   resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
   resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
  if os.getenv('PARSER_SANDBOX') == 'required':
   confine()
  docs=[]
  size=0
  for doc in MemoryLoader(sys.stdin.buffer.read(4*1024*1024+1),sys.argv[1],'document').lazy_load():
   size+=len(doc.page_content)
   if size>100000: raise ValueError('Document text exceeds 100,000 characters.')
   docs.append({'text':doc.page_content,'location':doc.metadata['location'],'needs_ocr':doc.metadata.get('needs_ocr',False)})
  print(json.dumps({'documents':docs}))
 except RuntimeError:
  print(json.dumps({'error':'Secure document parsing is unavailable on this host. Paste document text instead.'}))
 except Exception:
  print(json.dumps({'error':'Could not read this document. Use an unencrypted PDF (up to 100 pages) or valid DOCX.'}))
