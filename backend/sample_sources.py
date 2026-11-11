"""Pinned real sample documents. Source text is evidence, never instructions."""
import hashlib
import json
import wave
from pathlib import Path

from langchain_core.documents import Document

SAMPLES = Path(__file__).resolve().parents[1] / 'samples'
CATALOG = json.loads((SAMPLES / 'catalog.json').read_text(encoding='utf-8'))


def audio_script():
    script=json.loads((SAMPLES/'audio/family-boundary.es.json').read_text(encoding='utf-8'))
    if script['audio_sha256']!=hashlib.sha256((SAMPLES/'audio/family-boundary.es.wav').read_bytes()).hexdigest():
        raise ValueError('Audio timestamps do not match the recording.')
    with wave.open(str(SAMPLES/'audio/family-boundary.es.wav')) as audio:
        duration=audio.getnframes()/audio.getframerate()
    previous=0
    for part in script['turns']:
        if not 0<=previous<=part['start']<part['end']<=duration:
            raise ValueError('Audio timestamps are outside the recording.')
        previous=part['end']
    return script


def sample_documents(sample):
    item = CATALOG[sample]
    path = SAMPLES / 'documents' / item['filename']
    raw = path.read_bytes()
    if item.get('transcription'):
        data = json.loads((path.parent / item['transcription']).read_text(encoding='utf-8'))
        if data['pdf_sha256'] != hashlib.sha256(raw).hexdigest():
            raise ValueError('Sample transcription does not match the original PDF.')
        docs = [Document(page_content=text, metadata={
            'source':item['filename'], 'location':f'Page {index+1}',
            'transcription_method':data['method']}) for index,text in enumerate(data['pages'])]
    else:
        # Use the same bounded, offline parser as user-uploaded documents.
        from backend.parser_process import parse_document
        docs = parse_document(raw, 'pdf', item['filename'])
    return raw, docs
