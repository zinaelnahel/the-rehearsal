"""Bounded disposable parser process; OS/container sandboxing is still required."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import json
from langchain_core.documents import Document
from fastapi import HTTPException

_slots = threading.BoundedSemaphore(2)
_ocr_slots = threading.BoundedSemaphore(1)

def parse_document(raw, kind, name):
    if not _slots.acquire(blocking=False):
        raise HTTPException(503,'Document readers are busy. Try again shortly.')
    try:
        # Do not give the document parser provider keys or application secrets.
        env = {k: v for k, v in os.environ.items() if k.upper() in
               ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PYTHONPATH', 'LANG', 'PARSER_SANDBOX')}
        try:
            result = subprocess.run([sys.executable, '-m', 'backend.document_parser', kind],
                input=raw, capture_output=True, timeout=12, env=env,
                cwd=Path(__file__).resolve().parent.parent, check=False)
            if result.returncode or len(result.stdout) > 2_000_000:
                raise ValueError('Document parsing exceeded its limits. Try a smaller document.')
            data = json.loads(result.stdout)
            if 'error' in data:
                if data['error'].startswith('Secure document parsing is unavailable'):
                    raise HTTPException(503,data['error'])
                raise ValueError(data['error'])
            pages=data['documents']
            indexes=[index for index,page in enumerate(pages) if page.get('needs_ocr')]
            if kind=='pdf' and indexes:
                if len(indexes)>8:
                    raise ValueError('OCR supports up to 8 image-based pages. Upload a shorter PDF or paste the text.')
                if not _ocr_slots.acquire(blocking=False):
                    raise HTTPException(503,'The OCR reader is busy. Try again shortly.')
                try:
                    result=subprocess.run([sys.executable,'-m','backend.ocr_parser',','.join(map(str,indexes))],
                        input=raw,capture_output=True,timeout=38,env=env,
                        cwd=Path(__file__).resolve().parent.parent,check=False)
                    if result.returncode or len(result.stdout)>2_000_000:
                        raise ValueError('OCR exceeded its limits. Upload fewer image-based pages or paste the text.')
                    recognized=json.loads(result.stdout)
                    if 'error' in recognized:
                        message=recognized['error']
                        if message.startswith(('OCR is unavailable','Linux sandbox','Landlock','Seccomp','no_new_privs')):
                            raise HTTPException(503,'Secure OCR is unavailable on this host. Paste document text instead.')
                        raise ValueError(message)
                    seen=set()
                    for item in recognized['documents']:
                        index=item['page']
                        if index not in indexes or index in seen:raise ValueError('OCR returned invalid page references.')
                        seen.add(index)
                        if item['text'].strip():pages[index]['text']=item['text']
                        pages[index]['ocr']=True
                    if seen!=set(indexes):raise ValueError('OCR did not return all requested pages. Try a shorter PDF.')
                except subprocess.TimeoutExpired:
                    raise ValueError('OCR timed out. Upload fewer image-based pages or paste the text.') from None
                finally:_ocr_slots.release()
            if sum(len(page['text']) for page in pages)>100000:
                raise ValueError('Document text exceeds 100,000 characters.')
            return [Document(page_content=d['text'], metadata={'source': name, 'location': d['location'],'ocr':d.get('ocr',False)})
                    for d in pages]
        except subprocess.TimeoutExpired:
            raise ValueError('Document parsing timed out. Try a smaller text PDF or DOCX.') from None
    finally:
        _slots.release()
