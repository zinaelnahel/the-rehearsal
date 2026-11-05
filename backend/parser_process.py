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
            return [Document(page_content=d['text'], metadata={'source': name, 'location': d['location']})
                    for d in data['documents']]
        except subprocess.TimeoutExpired:
            raise ValueError('Document parsing timed out. Try a smaller text PDF or DOCX.') from None
    finally:
        _slots.release()
